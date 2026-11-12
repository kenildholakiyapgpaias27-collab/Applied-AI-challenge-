\set ON_ERROR_STOP 0
\set QUIET 1
insert into auth.users(id,email) values ('11111111-1111-1111-1111-111111111111','a@x.test'),('22222222-2222-2222-2222-222222222222','b@x.test');
create temp table results(test text, ok boolean);
grant all on results to anon, authenticated;
create or replace function pg_temp.t(name text, sql text, expect_ok boolean) returns void language plpgsql as $$
begin
  begin execute sql; insert into results values (name, expect_ok);
  exception when others then insert into results values (name || '  [' || sqlerrm || ']', not expect_ok); end;
end $$;
-- ---------- anon ----------
set role anon;
select pg_temp.t('anon reads products', 'select 1/(count(*)>800)::int from public.products', true);
select pg_temp.t('anon reads shades', 'select 1/(count(*)>500)::int from public.shades', true);
select pg_temp.t('anon reads catalogue version', 'select 1/(count(*)=1)::int from public.catalogue_meta', true);
select pg_temp.t('anon CANNOT write products', 'update public.products set price_inr=1 where id=''P1000''', false);
select pg_temp.t('anon CANNOT read profiles', 'select * from public.profiles', false);
select pg_temp.t('anon CANNOT create profile', 'insert into public.profiles(user_id,state,consent_version,consent_at) values (''11111111-1111-1111-1111-111111111111'',''{}'',''v1'',now())', false);
select pg_temp.t('anon logs an event', 'insert into public.events(session_id,name,props) values (gen_random_uuid(),''plan_shown'',''{"concern":"acne"}'')', true);
select pg_temp.t('anon CANNOT truncate events', 'truncate public.events', false);
select pg_temp.t('anon CANNOT delete events', 'delete from public.events', false);
select pg_temp.t('anon CANNOT read events', 'select * from public.events', false);
select pg_temp.t('unknown event name rejected', 'insert into public.events(session_id,name) values (gen_random_uuid(),''pregnancy_status'')', false);
select pg_temp.t('oversized event rejected', 'insert into public.events(session_id,name,props) values (gen_random_uuid(),''plan_shown'',jsonb_build_object(''x'',repeat(md5(random()::text),400)))', false);
select pg_temp.t('anon CANNOT call delete_my_data', 'select public.delete_my_data()', false);
select pg_temp.t('anon CANNOT read reports', 'select * from public.report_daily_events', false);
reset role;
-- ---------- user A ----------
set role authenticated; set request.jwt.claim.sub = '11111111-1111-1111-1111-111111111111';
select pg_temp.t('A: plan BEFORE consent rejected', 'insert into public.plans(made_at,concern,product_ids) values (now(),''acne'',array[''P1029''])', false);
select pg_temp.t('A: reaction BEFORE consent rejected', 'insert into public.reactions(reaction,source) values (''retinoids'',''profile'')', false);
select pg_temp.t('A: create profile with consent', 'insert into public.profiles(user_id,display_name,state,consent_version,consent_at) values (auth.uid(),''Asha'',''{"P":{"pregnancy":true}}'',''v1'',now())', true);
select pg_temp.t('A: save plan', 'insert into public.plans(made_at,concern,product_ids) values (''2026-11-01'',''acne'',array[''P1029'',''P1200'',''P1379''])', true);
select pg_temp.t('A: save check-in', 'insert into public.checkins(stage,results) values (''day3'',''{"P1029":"good","P1200":"sting"}'')', true);
select pg_temp.t('A: save reaction', 'insert into public.reactions(reaction,source,product_id) values (''niacinamide'',''checkin'',''P1200'')', true);
select pg_temp.t('A: CANNOT write a row as B', 'insert into public.plans(user_id,made_at,product_ids) values (''22222222-2222-2222-2222-222222222222'',now(),array[''P1''])', false);
select pg_temp.t('A: update own profile', 'update public.profiles set display_name=''Asha K'' where user_id=auth.uid()', true);
select pg_temp.t('A: CANNOT truncate profiles', 'truncate public.profiles cascade', false);
select pg_temp.t('A: CANNOT truncate products', 'truncate public.products cascade', false);
select pg_temp.t('A: CANNOT edit catalogue', 'update public.products set price_inr=1', false);
select pg_temp.t('A: CANNOT read events', 'select * from public.events', false);
reset role;
-- ---------- user B ----------
set role authenticated; set request.jwt.claim.sub = '22222222-2222-2222-2222-222222222222';
select pg_temp.t('B: sees 0 of A''s profiles', 'select 1/(count(*)=0)::int from public.profiles', true);
select pg_temp.t('B: sees 0 of A''s plans', 'select 1/(count(*)=0)::int from public.plans', true);
select pg_temp.t('B: sees 0 of A''s check-ins', 'select 1/(count(*)=0)::int from public.checkins', true);
select pg_temp.t('B: sees 0 of A''s reactions', 'select 1/(count(*)=0)::int from public.reactions', true);
select pg_temp.t('B: update of A''s profile changes nothing', 'do $x$ begin update public.profiles set display_name=''hacked''; if found then raise exception ''updated A''; end if; end $x$', true);
select pg_temp.t('B: delete of A''s plans removes nothing', 'do $x$ begin delete from public.plans; if found then raise exception ''deleted A''; end if; end $x$', true);
reset role;
-- ---------- A erases everything ----------
set role authenticated; set request.jwt.claim.sub = '11111111-1111-1111-1111-111111111111';
select pg_temp.t('A: delete_my_data()', 'select public.delete_my_data()', true);
reset role;
select pg_temp.t('after erasure: no rows or login left for A', $q$select 1/((select count(*) from public.profiles where user_id='11111111-1111-1111-1111-111111111111')+(select count(*) from public.plans where user_id='11111111-1111-1111-1111-111111111111')+(select count(*) from public.checkins where user_id='11111111-1111-1111-1111-111111111111')+(select count(*) from public.reactions where user_id='11111111-1111-1111-1111-111111111111')+(select count(*) from auth.users where id='11111111-1111-1111-1111-111111111111')=0)::int$q$, true);
select pg_temp.t('after erasure: B''s login untouched', $q$select 1/(count(*)=1)::int from auth.users where id='22222222-2222-2222-2222-222222222222'$q$, true);
-- inactive products are hidden
update public.products set active=false where id='P1614';
set role anon;
select pg_temp.t('inactive product hidden (and its shades)', $q$select 1/((select count(*) from public.products where id='P1614')+(select count(*) from public.shades where product_id='P1614')=0)::int$q$, true);
reset role;
update public.products set active=true where id='P1614';
\set QUIET 0
select case when ok then 'PASS' else 'FAIL' end as result, test from results;
select count(*) filter (where ok) as passed, count(*) filter (where not ok) as failed from results;
