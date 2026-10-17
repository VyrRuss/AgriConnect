# AgriConnect

A beginner-friendly Flask + MongoDB starter for a farmer support and agricultural marketplace website.

## Prerequisites

- Python 3.10 or newer
- MongoDB Community Server running locally, or a MongoDB Atlas connection URI
- VS Code with Python support

## 1. Open the project

Extract the `AgriConnect` folder and open it in VS Code.

## 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Or use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

## 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 4. Configure environment variables

Copy `.env.example` to a new file named `.env`. Change `SECRET_KEY` to a long random value. For local MongoDB, the default URI is usually:

```text
mongodb://localhost:27017/
```

Never commit `.env` to a public repository.

For card checkout, add your Stripe test secret key to `STRIPE_SECRET_KEY` in `.env`. Use Stripe's test keys while developing; card checkout remains unavailable until a key is configured. Card details are entered only on Stripe-hosted Checkout and are never stored by AgriConnect. Cash on delivery does not require Stripe.

For order confirmation SMS, copy the Twilio account SID, auth token, and SMS-capable sender number from your Twilio account into `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` in `.env` (the variable names are included in `.env.example`). Set `PUBLIC_BASE_URL` to the public HTTPS address of the deployed site so texted tracking links work outside the local machine. Restart the Flask server after editing `.env`. The SMS destination is the phone entered in delivery details; Indian 10-digit mobile numbers are sent with the `+91` country code, while numbers entered with `+` retain their country code. Never commit credentials or share them in chat. If Twilio is not configured or rejects a message, the order remains confirmed and the site clearly reports that no SMS was sent; order confirmation is not dependent on the SMS provider.

For Farmer Assist, add your NVIDIA NIM API key to `NVIDIA_KEY` in `.env` (`NVIDIA_API_KEY` is also accepted). The app uses NVIDIA's OpenAI-compatible chat completions endpoint and defaults to `deepseek-ai/deepseek-v4-flash`; if that model returns HTTP 410 Gone, it retries once with `meta/llama-3.3-70b-instruct`. Set `NVIDIA_MODEL` to an exact model ID enabled for your NVIDIA API key if needed. If the retry also fails, confirm the model is available to your NVIDIA account in the NVIDIA API Catalog. The key is used server-side and is never sent to the browser. The chat is available only to accounts registered with the Farmer role and retains a rolling window of recent messages so the conversation can continue through repeated questions. Existing accounts without a saved role are treated as customers. The assistant can respond to general questions as well as farming topics; its answers can be inaccurate and must not replace qualified medical, legal, financial, or local agricultural advice.

## 5. Start MongoDB

Make sure your MongoDB service is running. If you use MongoDB Atlas, put your Atlas connection URI in `.env` and allow your development IP in Atlas network access settings.

## 6. Add sample data (optional)

```bash
python -m database.sample_data
```

## 7. Run the site

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Check the application and database status at http://127.0.0.1:5000/health.

## Current scope

The app includes email/password registration with an account-created confirmation page, sign-in with a successful sign-in confirmation, a farmer-only AI problem-search assistant, a session-based shopping cart, cash-on-delivery orders, and Stripe-hosted card checkout. Checkout collects a delivery address for either payment method, and the confirmation page shows the submitted address after a successful order. Signed-in customers can use My Orders to review purchases and open a fulfillment-status timeline; it displays order stages, not a live GPS location. The fulfillment status is stored on each order and can be advanced by the order operator. Accounts and COD orders are stored in local SQLite (`instance/accounts.sqlite3`) when MongoDB is unavailable; set `ACCOUNT_DB_PATH` to choose a different location. MongoDB remains needed for persistent marketplace listings and paid card order storage. Add sample crops and products with `python -m database.sample_data`.

The marketplace includes sample crop listings grouped by cereals, fruits, oilseeds, pulses, and vegetables, with a category dropdown. Agricultural essentials have a second dropdown grouping seeds, electric kits, irrigation, and sowing equipment together, with separate fertilizer and agro-item groups; each group has at least four sample products. Sample product and crop illustrations are served locally. Crop price cards show **simulated illustrative quotes**, not a live exchange feed or financial data. Product catalog prices are the listed checkout prices. English, Hindi, and Kannada can be selected from the language menu.

Farmer Assist provides AI-generated general agricultural information, not a diagnosis or a substitute for local extension services. Confirm pesticide and other chemical use against the registered product label and a local expert. Seek qualified help for urgent illness or poisoning.

Do not expose the Flask development server to the public internet. Before production, configure HTTPS, strong secret and provider keys, Stripe live keys and webhooks, and appropriate account/order policies.

## Notes

- The hero photo uses a remote image URL, so internet access is needed to display it.
- Bootstrap is loaded from a CDN.
- MongoDB can be unavailable and the homepage still renders, but `/health` reports the database as unavailable.
- Replace placeholder content and validate all business rules before production deployment.
- Run the route tests with `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
