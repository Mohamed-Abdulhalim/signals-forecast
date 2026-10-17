create table if not exists public.prices (
  asset text not null,
  day date not null,
  close double precision not null check (close > 0),
  updated_at timestamptz not null default now(),
  primary key (asset, day)
);

create table if not exists public.forecasts (
  asset text not null,
  made_on date not null,
  kind text not null check (kind in ('live', 'backtest')),
  model text not null default 'v2',
  price double precision not null,
  trend text not null check (trend in ('up', 'down')),
  trend_strength double precision not null,
  vol_annual double precision not null,
  lo double precision not null,
  hi double precision not null,
  coverage double precision not null default 0.9,
  target_on date not null,
  created_at timestamptz not null default now(),
  primary key (asset, made_on, kind)
);

create index if not exists forecasts_kind_made_on on public.forecasts (kind, made_on desc);

create or replace view public.forecast_scores with (security_invoker = on) as
select f.*,
       o.day as actual_on,
       o.close as actual,
       case when o.close is null then null else (f.trend = 'up') = (o.close > f.price) end as trend_hit,
       case when o.close is null then null else o.close between f.lo and f.hi end as in_range,
       case when o.close is null then null else o.close > f.price end as went_up,
       case when o.close is null then null else abs(o.close / f.price - 1) end as abs_move
from public.forecasts f
left join lateral (
  select p.day, p.close from public.prices p
  where p.asset = f.asset and p.day >= f.target_on and p.day <= f.target_on + 7
  order by p.day limit 1
) o on true;

create or replace function public.dashboard()
returns json language sql stable security invoker set search_path = public as $$
  with assets as (select distinct asset from prices),
  hist as (
    select asset, json_agg(json_build_array(day, close) order by day) as history
    from prices where day >= current_date - 400 group by asset
  ),
  last2 as (
    select asset,
           (array_agg(close order by day desc))[1] as last,
           (array_agg(close order by day desc))[2] as prev,
           max(day) as last_day
    from prices where day >= current_date - 30 group by asset
  ),
  fc as (
    select distinct on (asset) asset, made_on, kind, price, trend, trend_strength, vol_annual, lo, hi, coverage, target_on
    from forecasts order by asset, (kind = 'live') desc, made_on desc
  ),
  stats as (
    select asset, kind, count(*) as n,
           avg(trend_hit::int) as trend_rate,
           avg(in_range::int) as range_rate,
           avg(went_up::int) as up_rate
    from forecast_scores where actual is not null group by asset, kind
  )
  select coalesce(json_agg(json_build_object(
    'asset', a.asset,
    'last', l.last, 'prev', l.prev, 'last_day', l.last_day,
    'history', h.history,
    'forecast', (select row_to_json(fc) from fc where fc.asset = a.asset),
    'stats', (select json_object_agg(s.kind, json_build_object('n', s.n, 'trend_rate', s.trend_rate, 'range_rate', s.range_rate, 'up_rate', s.up_rate)) from stats s where s.asset = a.asset)
  )), '[]'::json)
  from assets a left join last2 l using (asset) left join hist h using (asset);
$$;

create or replace function public.track_record()
returns json language sql stable security invoker set search_path = public as $$
  select json_build_object(
    'summary', (
      select coalesce(json_agg(row_to_json(s)), '[]'::json) from (
        select kind, asset, count(*) filter (where actual is not null) as completed,
               count(*) filter (where actual is null) as pending,
               avg(trend_hit::int) as trend_rate,
               avg(in_range::int) as range_rate,
               avg(went_up::int) as up_rate,
               min(made_on) as first_on, max(made_on) as last_on
        from forecast_scores group by kind, asset order by kind, asset
      ) s),
    'totals', (
      select coalesce(json_agg(row_to_json(t)), '[]'::json) from (
        select kind, count(*) filter (where actual is not null) as completed,
               count(*) filter (where actual is null) as pending,
               avg(trend_hit::int) as trend_rate,
               avg(in_range::int) as range_rate,
               avg(went_up::int) as up_rate,
               min(made_on) as first_on, max(made_on) as last_on
        from forecast_scores group by kind
      ) t),
    'recent', (
      select coalesce(json_agg(row_to_json(r)), '[]'::json) from (
        select asset, made_on, kind, price, trend, lo, hi, target_on, actual_on, actual, trend_hit, in_range
        from forecast_scores
        order by (kind = 'live') desc, made_on desc, asset
        limit 300
      ) r)
  );
$$;

alter table public.prices enable row level security;
alter table public.forecasts enable row level security;
drop policy if exists "public read prices" on public.prices;
drop policy if exists "public read forecasts" on public.forecasts;
create policy "public read prices" on public.prices for select to anon, authenticated using (true);
create policy "public read forecasts" on public.forecasts for select to anon, authenticated using (true);
revoke insert, update, delete, truncate on public.prices, public.forecasts from anon, authenticated;
grant execute on function public.dashboard(), public.track_record() to anon, authenticated;
