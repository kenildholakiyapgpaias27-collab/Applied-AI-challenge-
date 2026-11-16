-- Continue with Google: keep nothing from Google beyond what sign-in needs.
--
-- Supabase Auth copies the Google profile (name, photo URL, locale) into
-- auth.users.raw_user_meta_data and auth.identities.identity_data on every
-- sign-in. Aaina never uses these, so they are removed as they arrive.
-- Kept: the Google account id (sub), email and email_verified, which Supabase
-- needs to recognise the person and link their email-link and Google sign-ins.
-- The only name Aaina stores is the one the shopper types (profiles.display_name).

create or replace function public.strip_provider_profile() returns trigger
language plpgsql security definer set search_path = '' as $$
declare drop_keys text[] := array['name','full_name','given_name','family_name','nickname','avatar_url','picture','locale','preferred_username'];
begin
  if tg_table_name = 'users' then
    new.raw_user_meta_data := coalesce(new.raw_user_meta_data, '{}'::jsonb) - drop_keys;
  else
    new.identity_data := coalesce(new.identity_data, '{}'::jsonb) - drop_keys;
  end if;
  return new;
end $$;
revoke all on function public.strip_provider_profile() from public, anon, authenticated;

drop trigger if exists strip_provider_profile on auth.users;
create trigger strip_provider_profile before insert or update of raw_user_meta_data on auth.users
  for each row execute function public.strip_provider_profile();

drop trigger if exists strip_provider_profile on auth.identities;
create trigger strip_provider_profile before insert or update of identity_data on auth.identities
  for each row execute function public.strip_provider_profile();
