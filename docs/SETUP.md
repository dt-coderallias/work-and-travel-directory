# Setup

This takes about 30 minutes and costs nothing. You'll need a Google account, a GitHub account and a Streamlit Community Cloud account.

## 1. Create the back end

1. Go to [script.google.com](https://script.google.com) and choose **New project**. Name it `Directory back end`.
2. Delete the sample code, paste in all of `google/Code.gs`, and save.
3. Select `setup` in the function list and click **Run**.
4. Approve the permissions. Google warns that the app isn't verified because it's your own script. Choose **Advanced**, then **Go to Directory back end**.

`setup` creates two workbooks in your Drive: `Directory - Public` and `Directory - Private (do not share)`. Their links appear in the execution log.

## 2. Deploy the web app

1. Click **Deploy**, then **New deployment**.
2. Click the gear icon and choose **Web app**.
3. Set **Execute as** to **Me**, and **Who has access** to **Anyone**.
4. Click **Deploy** and copy the web app URL, which ends in `/exec`.

## 3. Load the existing data

1. In the private workbook, open the **Settings** tab and copy `submit_token`.
2. Put both values in `.streamlit/secrets.toml`:

   ```toml
   public_csv_url = "data/private/public_directory_seed.csv"
   submit_url = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"
   submit_token = "the token you copied"
   ```

3. Run `.venv\Scripts\python scripts\load_seed.py`. It should report 125 public rows.

This import works once and then closes itself.

## 4. Publish the public tab

**Do this in the public workbook only. Never publish the private workbook.**

1. Open `Directory - Public`.
2. Choose **File**, **Share**, **Publish to web**.
3. Under **Link**, choose the `Public Directory` tab and **Comma-separated values (.csv)**.
4. Open **Published content and settings** and tick **Automatically republish when changes are made**.
5. Click **Publish** and copy the link.

Don't share either workbook with anyone who isn't an administrator.

## 5. Put the code on GitHub

```
git add .
git commit -m "Initial directory"
gh repo create work-and-travel-directory --public --source=. --push
```

This repository is public, so check that `git ls-files` lists nothing under `data/` and no `secrets.toml`.

## 6. Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **Create app** and choose the repository, branch `main`, main file `app.py`.
3. Set a custom **App URL**. The default address includes your GitHub username.
4. Under **Advanced settings**, choose Python 3.13 and paste this into **Secrets**:

   ```toml
   public_csv_url = "the published CSV link from step 4"
   submit_url = "the web app URL from step 2"
   submit_token = "the token"
   ```

5. Click **Deploy**.
6. Open the app's **Settings**, then **Sharing**, and choose **This app is public and searchable**.

## 7. Check it

- Open the public link while signed out, on a phone.
- Add a test report from a private window, then find it within about 10 minutes.
- Set that report to **Removed** in the Review Queue and confirm it disappears.
- Open the private workbook's link in a private window and confirm access is denied.

## Changing things later

| Change | What to do |
|---|---|
| App code | Push to `main`. Streamlit redeploys by itself. |
| `Code.gs` | Paste the new code, then **Deploy**, **Manage deployments**, edit, **New version**. The URL stays the same. |
| Token | Change `SUBMIT_TOKEN` under **Project Settings**, **Script properties**, then update it in Streamlit secrets and in `Settings`. |
| Site name or star categories | Edit `directory/config.py` and push. |
| A new public column | Add the name to `PUBLIC_COLUMNS` in both `directory/config.py` and `google/Code.gs`, keeping the two lists in the same order. First add a matching column to every live tab that uses `PUBLIC_COLUMNS`: append it to `Directory - Public`, and insert it just before `original_details` in `Submissions` and just before `removed_at` in `Removed`. Then redeploy `Code.gs` straight away as a new version (see above). The back end copies rows by position, so the wrong order can put private text on the public sheet. |
