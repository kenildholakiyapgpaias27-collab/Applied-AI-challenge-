# Setting up "Continue with Google"

The code is ready. These steps need your own accounts, and they take about 20 minutes. Do them in this order.

You will need these values:

| | Value |
|---|---|
| Supabase project | `aaina-skin-advisor`, ref `qpevcwfpupmrgnfjodpt` |
| Supabase callback URL | `https://qpevcwfpupmrgnfjodpt.supabase.co/auth/v1/callback` |
| Live site | `https://kenildholakiyapgpaias27-collab.github.io/Applied-AI-challenge-/` |
| Local test site | `http://localhost:8765/` |

> **Never put the Google client secret in this repo, in `data/supabase.json`, or in any message.** It is pasted in one place only: the Supabase dashboard (step B1).

## A. Google Cloud Console

1. Go to <https://console.cloud.google.com/> and sign in with the Google account that should own the app. You might later need to hand it over, so a shared team account is better than a personal one.
2. At the top, open the project picker. Click **New project**, name it `Aaina Skin Advisor`, and click **Create**. Make sure the new project is selected.
3. Open **☰ → APIs & Services → OAuth consent screen**. On newer consoles this is **Google Auth Platform**. If it asks you to get started, click **Get started**.
4. **Branding / App information:**
   1. **App name:** `Aaina Skin Advisor`.
   2. **User support email:** your team email.
   3. **App logo:** leave it empty for now. Adding a logo triggers Google's brand review.
   4. **App domain:**
      - **Application home page:** `https://kenildholakiyapgpaias27-collab.github.io/Applied-AI-challenge-/`
      - **Privacy policy link:** the URL of a public privacy-policy page. The app has no separate page yet. In Testing mode you can leave this empty; for Production it is required (see section D).
   5. **Authorised domains:** add `qpevcwfpupmrgnfjodpt.supabase.co`. Also add `kenildholakiyapgpaias27-collab.github.io` if the console accepts it.
   6. **Developer contact email:** your team email.
   7. Save.
5. **Audience / User type:** choose **External**. Leave the **Publishing status** on **Testing**.
6. **Test users:** click **Add users** and add every Google address that will try the app, including your own. While the app is in Testing, only these addresses can sign in, up to 100 of them. Anyone else sees "Access blocked".
7. **Data access / Scopes:** click **Add or remove scopes** and tick only these three:
   - `openid`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`

   Save. These are non-sensitive scopes, so Google does not need a security review for them.
8. **Clients / Credentials:** click **Create client** (or **+ Create credentials → OAuth client ID**).
   1. **Application type:** `Web application`.
   2. **Name:** `Aaina Supabase`.
   3. **Authorised JavaScript origins:** add `https://kenildholakiyapgpaias27-collab.github.io` and `http://localhost:8765`. These are optional for this flow, but harmless.
   4. **Authorised redirect URIs:** add exactly `https://qpevcwfpupmrgnfjodpt.supabase.co/auth/v1/callback`. This must be the Supabase URL, not the GitHub Pages URL.
   5. Click **Create**.
9. A dialog shows the **Client ID** and **Client secret**. Copy both into a password manager now; don't paste them into chat or a file in the repo.

## B. Supabase dashboard

1. Open <https://supabase.com/dashboard/project/qpevcwfpupmrgnfjodpt>, then **Authentication → Sign In / Providers → Google**.
   1. Turn on **Enable Sign in with Google**.
   2. **Client IDs:** paste the Client ID.
   3. **Client Secret (for OAuth):** paste the Client secret.
   4. Leave **Skip nonce checks** off.
   5. Leave **Allow users without an email** off.
   6. Click **Save**.
2. **Authentication → URL Configuration:**
   1. **Site URL:** `https://kenildholakiyapgpaias27-collab.github.io/Applied-AI-challenge-/`
   2. **Redirect URLs:** make sure these two are both listed. Remove anything else you don't recognise.
      - `https://kenildholakiyapgpaias27-collab.github.io/Applied-AI-challenge-/**`
      - `http://localhost:8765/**`
   3. Save.
3. **Automatic account linking.** Supabase links a Google sign-in to an existing email-link account when both use the same verified email. This is on by default, and there is nothing to switch on. To check it worked after your first test (step C6), run this in **SQL Editor**:
   ```sql
   select u.email, array_agg(i.provider order by i.provider) as methods
   from auth.users u join auth.identities i on i.user_id = u.id
   group by u.email;
   ```
   Each email should appear **once**, with `{email,google}` if both methods were used. If the same email appears twice, see "If linking fails" below.
4. **Keep only what Aaina needs from Google.** In **SQL Editor**, open `supabase/migrations/20261116000000_google_minimal_profile.sql` from this repo, paste it in, and click **Run**. It removes the Google name and photo URL that Supabase Auth copies into `auth.users` and `auth.identities`. It keeps the Google account id and email, which linking needs. To check it:
   ```sql
   select raw_user_meta_data from auth.users;   -- no "name", "full_name", "picture" or "avatar_url"
   ```

## C. Test it (in Testing mode)

1. Merge the PR (or open the branch's build locally: `python3 -m http.server 8765`, then visit `http://localhost:8765/index.html`).
2. Finish a plan. In the **Keep your plan on any device** box, **Continue with Google** should stay greyed out until you tick the consent box.
3. Tick the box, then click **Continue with Google**. Pick a **test user** account and approve. You should come back to the page, signed in, with no `?code=` in the address bar, and your plan should be saved.
4. Open the page with `#try-on` at the end and sign in with Google from there (the welcome line has the button too). You should come back to `#try-on`.
5. Click **Continue with Google**, then **Cancel** on Google's screen. You should see "Google sign-in was cancelled" and still be signed out.
6. Sign out. Then use **Sign in with email** with the same Gmail address. You should see the same saved plan, and the SQL in B3 should show one account.
7. **Delete my answers → Delete everything**. In SQL Editor, `select count(*) from auth.identities where email = '<that address>'` should return `0`.

## D. Moving the Google app from Testing to Production

In Testing, only listed test users can sign in. Google also asks them to approve again after 7 days, because grants for Testing apps expire.

To open sign-in to everyone:

1. **Privacy policy:** publish one at a public URL on a domain you control. It should say what Aaina receives from Google (account id and email), that the name and photo are discarded, what is stored with consent, and how to delete everything. Put the link in **Branding**.
2. **Home page and domains:** the home page, the privacy policy and every authorised domain must be on a domain you can prove you own, through Google Search Console. A `github.io` sub-path can't be verified as yours. Use a custom domain for the site, and ideally a [Supabase custom domain](https://supabase.com/docs/guides/platform/custom-domains) for the auth callback, so Google's screen shows your domain instead of `supabase.co`. If you use a custom auth domain, update the redirect URI in A8.4.
3. **Audience → Publish app → Confirm.** With only `openid`, `email` and `profile`, no security assessment is needed. Google may still run a short **brand verification** (app name, logo, domains) before your name and logo show on the consent screen. Until then, users see the app's domain.
4. After publishing, the test-user list no longer matters, and the 7-day re-approval goes away.
5. Production apps also need SMTP for the email link at real volume (Supabase **Authentication → Emails**, see README).

## If linking fails (two accounts for one person)

If the SQL in B3 shows the same email twice, Supabase did not link the identities. This can happen if the email-link account was created but its address was never confirmed. The page cannot fix this on its own, because merging accounts needs the service role. Two fixes:

- **Manual:** in **Authentication → Users**, delete the unconfirmed duplicate (it has no saved plan), then sign in again.
- **In the app (a follow-up):** a small Edge Function, using the service role, that calls Supabase's `linkIdentity` for a signed-in user who proves both sign-ins. Until then, the app shows whatever is saved in the account you signed in to.

## What the browser cannot do

- **Revoking Google's grant:** "Delete my answers" removes the Aaina login, its Google identity and every row. It does not remove "Aaina" from the user's Google account permissions, because the page never holds a Google token. Users can remove it at <https://myaccount.google.com/permissions>. Doing it automatically would need an Edge Function holding the Google provider token, which Aaina deliberately doesn't keep.
