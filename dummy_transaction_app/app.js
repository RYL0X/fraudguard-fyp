/* ── SecurePay — Dummy Transaction App JS ─────────────────────────────
   Sends payments to FraudGuard backend for real ML analysis.
   API endpoint: POST /api/external/transaction
──────────────────────────────────────────────────────────────────────── */

const API_BASE = window.location.origin;

async function submitPayment() {
  const btn     = document.getElementById('pay-btn');
  const btnText = document.getElementById('pay-btn-text');

  // ── Gather form values ──────────────────────────────────────────────
  const customer_name  = document.getElementById('customer_name').value.trim();
  const customer_email = document.getElementById('customer_email').value.trim();
  const card_last4     = document.getElementById('card_last4').value.trim();
  const amount         = parseFloat(document.getElementById('amount').value);
  const merchant       = document.getElementById('merchant').value.trim();
  const category       = document.getElementById('category').value;
  const location       = document.getElementById('location').value.trim();
  const is_foreign     = document.getElementById('is_foreign').checked ? 1 : 0;

  // ── Client-side validation ─────────────────────────────────────────
  if (!customer_name || !customer_email || !card_last4 || !amount || !merchant || !category || !location) {
    showFormError('Please fill in all required fields.');
    return;
  }
  if (!/^\d{4}$/.test(card_last4)) {
    showFormError('Card last 4 digits must be exactly 4 numbers.');
    return;
  }
  if (isNaN(amount) || amount <= 0) {
    showFormError('Please enter a valid amount greater than 0.');
    return;
  }

  // ── Show loading state ─────────────────────────────────────────────
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div><span>Processing…</span>';

  const payload = {
    customer_name,
    customer_email,
    card_last4,
    amount,
    merchant,
    category,
    location,
    is_foreign,
    hour:        new Date().getHours(),
    day_of_week: new Date().getDay(),
    source:      'dummy_app',
  };

  try {
    const response = await fetch(`${API_BASE}/api/external/transaction`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || `Server error: ${response.status}`);
    }

    showResult(result, payload);

  } catch (err) {
    btn.disabled = false;
    btn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
      <span>Pay Now</span>`;
    showFormError(err.message || 'Unable to connect to FraudGuard API. Please try again.');
  }
}

// ── Render result screen ────────────────────────────────────────────────
function showResult(result, payload) {
  const formScreen   = document.getElementById('form-screen');
  const resultScreen = document.getElementById('result-screen');

  const status     = result.status || 'approved';
  const isBlocked  = status === 'blocked';
  const isReview   = status === 'under_review';
  const isApproved = status === 'approved';

  const confidencePct = ((result.confidence || 0) * 100).toFixed(1) + '%';
  const riskLevel     = result.risk_level || 'LOW';
  const txnId         = result.transaction_id || '—';
  const amountFmt     = '$' + parseFloat(payload.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // Icon
  let iconHtml, titleText, messageText, riskCls;

  if (isBlocked) {
    iconHtml    = `<div class="result-icon blocked"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div>`;
    titleText   = 'Payment Blocked';
    messageText = 'Suspicious activity was detected on this transaction. Your bank has been notified and a fraud alert email will be sent to you shortly.';
    riskCls     = 'badge-blocked';
  } else if (isReview) {
    iconHtml    = `<div class="result-icon warning"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>`;
    titleText   = 'Payment Under Review';
    messageText = 'Your transaction has been flagged for review by FraudGuard AI. Our team is analyzing this transaction and you will be notified via email.';
    riskCls     = 'badge-review';
  } else {
    iconHtml    = `<div class="result-icon success"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg></div>`;
    titleText   = 'Transaction Approved';
    messageText = 'Your payment was processed successfully and verified as safe by FraudGuard AI.';
    riskCls     = 'badge-approved';
  }

  const levelCls = riskLevel === 'HIGH' ? 'badge-high' : riskLevel === 'MEDIUM' ? 'badge-medium' : 'badge-low';

  // Build detail rows
  const rows = [
    ['Amount',       amountFmt,                                    ''],
    ['Merchant',     payload.merchant,                             ''],
    ['Category',     (payload.category || '—').replace(/_/g,' '), ''],
    ['Location',     payload.location,                             ''],
    ['Status',       titleText,                                    riskCls],
    ['Risk Level',   riskLevel,                                    levelCls],
    ['Confidence',   confidencePct,                                levelCls],
    ['Transaction ID', `<span class="txn-id-val" title="${txnId}">${txnId}</span>`, 'txn-id'],
  ];

  const detailsHtml = rows.map(([key, val, cls]) => `
    <div class="detail-row">
      <span class="detail-key">${key}</span>
      <span class="detail-val ${cls}">${val}</span>
    </div>`).join('');

  document.getElementById('result-icon-wrap').innerHTML = iconHtml;
  document.getElementById('result-title').textContent   = titleText;
  document.getElementById('result-message').textContent = messageText;
  document.getElementById('result-details').innerHTML   = detailsHtml;

  const helpline = document.getElementById('helpline-wrap');
  helpline.style.display = isBlocked ? 'flex' : 'none';

  formScreen.style.display   = 'none';
  resultScreen.style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Reset to form ───────────────────────────────────────────────────────
function resetForm() {
  document.getElementById('payment-form').reset();
  clearFormError();
  document.getElementById('form-screen').style.display   = 'block';
  document.getElementById('result-screen').style.display = 'none';

  // Restore pay button
  document.getElementById('pay-btn').disabled = false;
  document.getElementById('pay-btn').innerHTML = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
    <span id="pay-btn-text">Pay Now</span>`;

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Form error helpers ──────────────────────────────────────────────────
function showFormError(msg) {
  clearFormError();
  const err = document.createElement('p');
  err.id        = 'form-error';
  err.textContent = '⚠ ' + msg;
  err.style.cssText = 'color:#dc2626;font-size:.83rem;font-weight:600;margin-top:12px;text-align:center;background:#fef2f2;border:1px solid #fecaca;padding:10px 14px;border-radius:8px;';
  const form = document.getElementById('payment-form');
  form.appendChild(err);
}

function clearFormError() {
  const existing = document.getElementById('form-error');
  if (existing) existing.remove();
}
