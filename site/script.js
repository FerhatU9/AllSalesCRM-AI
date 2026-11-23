(() => {
  "use strict";
  const data = {
    discount: {
      src: "./assets/discount-approval.png",
      title: "Discount review",
      description: "A fictional discount request flagged for human review.",
      alt: "Actual AllSales CRM screenshot documenting a fictional discount approval scenario",
      count: "01 / 03"
    },
    security: {
      src: "./assets/security-escalation.png",
      title: "Security escalation",
      description: "A fictional security concern routed for escalation.",
      alt: "Actual AllSales CRM screenshot documenting a fictional security escalation scenario",
      count: "02 / 03"
    },
    incomplete: {
      src: "./assets/incomplete-lead.png",
      title: "Incomplete lead",
      description: "Missing lead information prevents a final qualification tier.",
      alt: "Actual AllSales CRM screenshot showing how incomplete fictional lead data is handled",
      count: "03 / 03"
    }
  };
  const buttons = Array.from(document.querySelectorAll("[data-screen]"));
  const image = document.getElementById("screen-image");
  const link = document.getElementById("screen-link");
  const title = document.getElementById("screen-title");
  const description = document.getElementById("screen-description");
  const count = document.getElementById("screen-count");
  if (!image || !link || !title || !description || !count) return;
  buttons.forEach(button => {
    button.addEventListener("click", () => {
      const selection = data[button.dataset.screen];
      if (!selection) return;
      buttons.forEach(other => {
        const selected = other === button;
        other.classList.toggle("is-active", selected);
        other.setAttribute("aria-pressed", String(selected));
      });
      image.src = selection.src;
      image.alt = selection.alt;
      link.href = selection.src;
      link.setAttribute("aria-label", "Open the " + selection.title + " screenshot in full size");
      title.textContent = selection.title;
      description.textContent = selection.description;
      count.textContent = selection.count;
    });
  });
})();
