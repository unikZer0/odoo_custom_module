/** Slip2Go front-end helper for verifying PromptPay payments. */
(function () {
    const readFileAsDataURL = (file) => new Promise((resolve, reject) => {
        if (!file) {
            resolve(null);
            return;
        }
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });

    const updateAlert = (el, type, message) => {
        if (!el) {
            return;
        }
        el.className = `alert alert-${type}`;
        el.textContent = message;
    };

    const handleVerifyClick = async (rootEl) => {
        const verifyBtn = rootEl.querySelector('[data-role="slip2go-verify"]');
        const qrField = rootEl.querySelector('[data-role="slip2go-qr"]');
        const resultBox = rootEl.querySelector('[data-role="slip2go-result"]');
        const fileInput = rootEl.querySelector('[data-role="slip2go-file"]');
        const invoiceId = rootEl.dataset.invoiceId;
        const rawTxId = rootEl.dataset.transactionId;
        const transactionId = rawTxId && rawTxId !== 'False' ? rawTxId : null;
        const accessToken = rootEl.dataset.accessToken;
        const qrPayload = (qrField && qrField.value.trim()) || rootEl.dataset.qrPayload;
        const verifyUrl = rootEl.dataset.verifyUrl;

        if (!invoiceId || !verifyUrl) {
            updateAlert(resultBox, 'danger', 'Missing invoice context.');
            return;
        }

        verifyBtn.disabled = true;
        updateAlert(resultBox, 'info', 'Verifying with Slip2Go ...');

        let keepDisabled = false;
        try {
            const file = fileInput && fileInput.files.length ? fileInput.files[0] : null;
            const imageData = await readFileAsDataURL(file);
            const payload = {
                invoice_id: invoiceId,
                qr: qrPayload,
            };
            if (transactionId) {
                payload.transaction_id = transactionId;
            }
            if (accessToken && accessToken !== 'False') {
                payload.access_token = accessToken;
            }
            if (imageData) {
                payload.image = imageData;
                payload.filename = file.name;
                payload.mimetype = file.type;
            }

            const response = await fetch(verifyUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            const body = await response.json();
            if (body.status === 'ok') {
                updateAlert(resultBox, 'success', body.message || 'Payment verified. Please wait for confirmation.');
                keepDisabled = true;
            } else {
                updateAlert(resultBox, 'danger', body.message || 'Verification failed.');
            }
        } catch (err) {
            updateAlert(resultBox, 'danger', err.message || String(err));
        } finally {
            if (!keepDisabled) {
                verifyBtn.disabled = false;
            }
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        const rootEl = document.getElementById('slip2go-payment');
        if (!rootEl) {
            return;
        }
        const verifyBtn = rootEl.querySelector('[data-role="slip2go-verify"]');
        if (verifyBtn) {
            verifyBtn.addEventListener('click', (ev) => {
                ev.preventDefault();
                handleVerifyClick(rootEl);
            });
        }
    });
})();

