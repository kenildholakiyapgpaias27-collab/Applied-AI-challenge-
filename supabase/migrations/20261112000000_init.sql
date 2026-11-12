-- Aaina AI Skin Advisor: database schema for Supabase (Postgres 15+)
--
-- Run once in the Supabase SQL editor (or `supabase db push`), then load
-- supabase/seed.sql to fill the catalogue.
--
-- Four kinds of data, with different rules:
--   1. Catalogue (products, shades, catalogue_meta) .... public, read-only for the app
--   2. Account data (profiles, plans, checkins, reactions)
--        ... sensitive (pregnancy, reactions). Only written after the user signs in
--            AND ticks consent. Row-level security: each user sees only their own rows.
--   3. Anonymous analytics (events) .... insert-only, no personal fields, nobody can
--        read it through the API (query it from the dashboard / service role).
--   4. Erasure: delete_my_data() removes every account row and the login itself.

-- ---------------------------------------------------------------------------
-- 1. Catalogue
-- ---------------------------------------------------------------------------
create table if not exists public.products (
  id               text primary key,                 -- e.g. P1614
  brand            text not null,
  name             text not null,
  category         text not null,
  price_inr        numeric(10,2),                    -- null = price not listed
  size             text,
  key_actives      text,                             -- "Niacinamide 10% + Zinc 1%"
  inci             text,                             -- full ingredient list; null = not disclosed
  skin_types       text[] not null default '{}',     -- oily / combination / normal / dry
  concerns         text[] not null default '{}',
  -- the catalogue's own flags; the app re-derives these from the INCI and keeps the stricter
  contains_fragrance       boolean not null default false,
  contains_essential_oils  boolean not null default false,
  contains_drying_alcohol  boolean not null default false,
  contains_retinoid        boolean not null default false,
  contains_aha             boolean not null default false,
  contains_bha             boolean not null default false,
  pregnancy_caution        boolean not null default false,
  comedogenic_risk text check (comedogenic_risk in ('low','medium','high')),
  finish           text,
  spf              numeric(4,1),
  pa_rating        text,
  is_sponsored     boolean not null default false,
  active           boolean not null default true,    -- false = hidden from the app, kept for history
  updated_at       timestamptz not null default now()
);
create index if not exists products_category_idx on public.products (category) where active;

create table if not exists public.shades (
  product_id  text not null references public.products(id) on delete cascade,
  shade_name  text not null,
  depth       smallint not null check (depth between 1 and 10),   -- Monk scale
  undertone   text not null check (undertone in ('cool','neutral','warm','olive')),
  hex         text check (hex ~ '^#[0-9a-fA-F]{6}$'),
  coverage    text,
  sort_order  smallint not null default 0,
  primary key (product_id, shade_name)
);

-- One row. The app compares this with the version it was built with and only
-- downloads the catalogue when they differ.
create table if not exists public.catalogue_meta (
  id          boolean primary key default true check (id),
  version     text not null,
  updated_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 2. Account data (owner-only)
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
  user_id          uuid primary key references auth.users(id) on delete cascade,
  display_name     text check (char_length(display_name) <= 24),
  -- the app's saved state (answers, plan ids, check-in dates). It can include
  -- pregnancy status and reactions, which is why consent is required first.
  state            jsonb not null default '{}'::jsonb check (pg_column_size(state) < 200000),
  consent_version  text not null,
  consent_at       timestamptz not null,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create table if not exists public.plans (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade default auth.uid(),
  made_at      timestamptz not null,                 -- when the plan was first made (META.planAt)
  concern      text,
  product_ids  text[] not null,                      -- in slot order; 'keep' = user's own product
  extras       jsonb not null default '[]'::jsonb,
  updated_at   timestamptz not null default now(),
  unique (user_id, made_at)
);

create table if not exists public.checkins (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade default auth.uid(),
  plan_id    uuid references public.plans(id) on delete set null,
  stage      text not null check (stage in ('day3','week2','manual')),
  results    jsonb not null,                         -- { "P1029": "good" | "sting" | "break" | "notyet" | "stop" ... }
  created_at timestamptz not null default now()
);
create index if not exists checkins_user_idx on public.checkins (user_id, created_at desc);

create table if not exists public.reactions (
  user_id     uuid not null references auth.users(id) on delete cascade default auth.uid(),
  reaction    text not null check (char_length(reaction) <= 40),   -- e.g. 'retinoids', 'tea tree oil'
  source      text not null check (source in ('profile','checkin')),
  product_id  text references public.products(id) on delete set null,
  created_at  timestamptz not null default now(),
  primary key (user_id, reaction)
);

-- keep updated_at honest
create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$ begin new.updated_at := now(); return new; end $$;
drop trigger if exists profiles_touch on public.profiles;
create trigger profiles_touch before update on public.profiles for each row execute function public.touch_updated_at();
drop trigger if exists plans_touch on public.plans;
create trigger plans_touch before update on public.plans for each row execute function public.touch_updated_at();
drop trigger if exists products_touch on public.products;
create trigger products_touch before update on public.products for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------------------
-- 3. Anonymous analytics (insert-only)
-- ---------------------------------------------------------------------------
create table if not exists public.events (
  id          bigint generated always as identity primary key,
  session_id  uuid not null,                         -- random per browser tab, not linked to a login
  name        text not null check (name in
                ('plan_shown','product_swapped','plan_tuned','checkin_saved','set_aside','catalogue_refreshed')),
  props       jsonb not null default '{}'::jsonb check (pg_column_size(props) < 4000),
  created_at  timestamptz not null default now()
);
create index if not exists events_name_time_idx on public.events (name, created_at desc);

-- ---------------------------------------------------------------------------
-- Row-level security
-- ---------------------------------------------------------------------------
alter table public.products       enable row level security;
alter table public.shades         enable row level security;
alter table public.catalogue_meta enable row level security;
alter table public.profiles       enable row level security;
alter table public.plans          enable row level security;
alter table public.checkins       enable row level security;
alter table public.reactions      enable row level security;
alter table public.events         enable row level security;

-- catalogue: anyone may read active products; nobody writes through the API
drop policy if exists "read active products" on public.products;
create policy "read active products" on public.products for select to anon, authenticated using (active);
drop policy if exists "read shades" on public.shades;
create policy "read shades" on public.shades for select to anon, authenticated
  using (exists (select 1 from public.products p where p.id = product_id and p.active));
drop policy if exists "read catalogue version" on public.catalogue_meta;
create policy "read catalogue version" on public.catalogue_meta for select to anon, authenticated using (true);

-- account tables: the signed-in owner only
drop policy if exists "own profile" on public.profiles;
create policy "own profile" on public.profiles for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
drop policy if exists "own plans" on public.plans;
create policy "own plans" on public.plans for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
drop policy if exists "own checkins" on public.checkins;
create policy "own checkins" on public.checkins for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
drop policy if exists "own reactions" on public.reactions;
create policy "own reactions" on public.reactions for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

-- account rows can only exist for users who gave consent: a profile row (which
-- carries consent_at) must exist before plans/checkins/reactions are accepted
drop policy if exists "consent before plans" on public.plans;
create policy "consent before plans" on public.plans as restrictive for insert to authenticated
  with check (exists (select 1 from public.profiles pr where pr.user_id = (select auth.uid())));
drop policy if exists "consent before checkins" on public.checkins;
create policy "consent before checkins" on public.checkins as restrictive for insert to authenticated
  with check (exists (select 1 from public.profiles pr where pr.user_id = (select auth.uid())));
drop policy if exists "consent before reactions" on public.reactions;
create policy "consent before reactions" on public.reactions as restrictive for insert to authenticated
  with check (exists (select 1 from public.profiles pr where pr.user_id = (select auth.uid())));

-- analytics: write-only from the browser
drop policy if exists "log anonymous events" on public.events;
create policy "log anonymous events" on public.events for insert to anon, authenticated with check (true);

-- Table privileges. Supabase grants ALL on new tables to anon and authenticated by
-- default and relies on RLS. That default includes TRUNCATE, which RLS does not
-- check (any signed-in user could empty everyone's profiles). So: start from
-- nothing, then grant exactly what the app needs. RLS still applies on top.
revoke all on public.products, public.shades, public.catalogue_meta,
              public.profiles, public.plans, public.checkins, public.reactions,
              public.events from anon, authenticated;
grant select on public.products, public.shades, public.catalogue_meta to anon, authenticated;
grant select, insert, update, delete on public.profiles, public.plans, public.checkins, public.reactions to authenticated;
grant insert on public.events to anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Right to erasure: delete everything for the signed-in user, login included
-- ---------------------------------------------------------------------------
create or replace function public.delete_my_data() returns void
language plpgsql security definer set search_path = '' as $$
declare uid uuid := auth.uid();
begin
  if uid is null then raise exception 'not signed in'; end if;
  delete from public.checkins  where user_id = uid;
  delete from public.reactions where user_id = uid;
  delete from public.plans     where user_id = uid;
  delete from public.profiles  where user_id = uid;
  delete from auth.users       where id = uid;
end $$;
revoke all on function public.delete_my_data() from public, anon;
grant execute on function public.delete_my_data() to authenticated;

-- ---------------------------------------------------------------------------
-- Reporting views for the dashboard (service role / SQL editor only)
-- ---------------------------------------------------------------------------
create or replace view public.report_checkin_outcomes with (security_invoker = true) as
select r.key as product_id, p.name, p.category, r.value as outcome, count(*) as n
from public.checkins c
cross join lateral jsonb_each_text(c.results) r
left join public.products p on p.id = r.key
group by 1,2,3,4;

create or replace view public.report_daily_events with (security_invoker = true) as
select date_trunc('day', created_at) as day, name, count(*) as n, count(distinct session_id) as sessions
from public.events group by 1,2;

revoke all on public.report_checkin_outcomes, public.report_daily_events from anon, authenticated;
