document.addEventListener("DOMContentLoaded", () => {
  const year = document.getElementById("currentYear");
  if (year) year.textContent = new Date().getFullYear();

  document.querySelectorAll("[data-market-price]").forEach((priceNode) => {
    const basePrice = Number(priceNode.dataset.basePrice);
    let currentPrice = basePrice;
    const changeNode = priceNode.closest(".p-3")?.querySelector("[data-market-change]");
    const baseChange = Number(changeNode?.dataset.baseChange || 0);
    const updateQuote = () => {
      currentPrice = Math.max(0.01, currentPrice * (1 + (Math.random() - 0.49) * 0.006));
      priceNode.textContent = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(currentPrice);
      if (changeNode && basePrice) {
        const percent = baseChange + ((currentPrice / basePrice) - 1) * 100;
        changeNode.textContent = `${percent >= 0 ? "▲ +" : "▼ "}${percent.toFixed(1)}%`;
        changeNode.classList.toggle("market-down", percent < 0);
        changeNode.classList.toggle("market-up", percent >= 0);
      }
    };
    window.setInterval(updateQuote, 5000);
  });

  const categoryFilter = document.getElementById("cropCategoryFilter");
  const cropListings = [...document.querySelectorAll(".crop-listing")];
  const categoryCount = document.getElementById("cropCategoryCount");
  const filterCrops = () => {
    if (!categoryFilter) return;
    const selectedCategory = categoryFilter.value;
    let visibleCount = 0;
    cropListings.forEach((listing) => {
      const matches = selectedCategory === "all" || listing.dataset.cropCategory === selectedCategory;
      listing.classList.toggle("d-none", !matches);
      if (matches) visibleCount += 1;
    });
    if (categoryCount) categoryCount.textContent = `${visibleCount} crops shown`;
  };
  if (categoryFilter) {
    categoryFilter.addEventListener("change", filterCrops);
    filterCrops();
  }

  const supplyFilter = document.getElementById("supplyCategoryFilter");
  const supplyProducts = [...document.querySelectorAll(".supply-product")];
  const supplyCount = document.getElementById("supplyCategoryCount");
  const filterSupplies = () => {
    if (!supplyFilter) return;
    const selectedCategory = supplyFilter.value;
    let visibleCount = 0;
    supplyProducts.forEach((product) => {
      const matches = selectedCategory === "all" || product.dataset.supplyCategory === selectedCategory;
      product.classList.toggle("d-none", !matches);
      if (matches) visibleCount += 1;
    });
    if (supplyCount) supplyCount.textContent = `${visibleCount} products shown`;
  };
  if (supplyFilter) {
    supplyFilter.addEventListener("change", filterSupplies);
    filterSupplies();
  }

  // Close the mobile navigation after a user selects an in-page link.
  document.querySelectorAll("#mainNav .nav-link[href^='#']").forEach((link) => {
    link.addEventListener("click", () => {
      const nav = document.getElementById("mainNav");
      if (nav && nav.classList.contains("show") && window.bootstrap) {
        window.bootstrap.Collapse.getOrCreateInstance(nav).hide();
      }
    });
  });
});
