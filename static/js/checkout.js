document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("checkoutForm");
  const deliveryFields = document.getElementById("deliveryFields");
  const button = document.getElementById("placeOrderButton");
  const paymentNote = document.getElementById("paymentNote");
  if (!form || !deliveryFields || !button || !paymentNote) return;

  const paymentOptions = form.querySelectorAll("input[name='payment_method']");
  const updatePayment = () => {
    const selected = form.querySelector("input[name='payment_method']:checked");
    deliveryFields.hidden = !selected;
    deliveryFields.disabled = !selected;
    if (!selected) {
      button.textContent = "Place order";
      paymentNote.textContent = "Choose a payment method to continue.";
      return;
    }
    if (selected.value === "card") {
      button.textContent = "Continue to secure card payment";
      paymentNote.textContent = "You’ll continue to Stripe to securely complete payment.";
    } else {
      button.textContent = "Place order";
      paymentNote.textContent = "You’ll see your order confirmation after placing the order.";
    }
  };

  paymentOptions.forEach((option) => option.addEventListener("change", updatePayment));
  form.addEventListener("submit", () => {
    button.disabled = true;
    button.textContent = "Processing your order…";
  });
  updatePayment();
});
