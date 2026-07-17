function formatPrice(price) {
    return `$${Number(price).toLocaleString("es-MX", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    })} MXN`;
}

function formatDuration(minutes) {
    if (minutes === 1440) return "Día completo";
    if (minutes % 60 === 0) return `${minutes / 60} hora${minutes === 60 ? "" : "s"}`;
    return `${minutes} min`;
}

function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = value || "Acceso a internet CofiNet+.";
    return element.innerHTML;
}

function renderMobilePlan(plan, index) {
    const highlighted = index === 2;
    const cardClass = highlighted
        ? "flex-shrink-0 w-[140px] bg-cofiOlive text-black rounded-xl p-3.5 flex flex-col justify-between snap-center shadow-lg transition-all text-left"
        : "flex-shrink-0 w-[140px] bg-zinc-900 border border-zinc-800/80 rounded-xl p-3.5 flex flex-col justify-between snap-center glow-hover transition-all text-left";
    const titleClass = highlighted ? "text-xs font-black uppercase tracking-wider font-grotesk" : "text-xs font-bold text-white uppercase tracking-wider font-grotesk";
    const durationClass = highlighted ? "text-[7px] text-black/60 font-black uppercase tracking-widest" : "text-[7px] text-gray-500 font-bold uppercase tracking-widest";
    const textClass = highlighted ? "text-[7px] text-black/70 font-bold" : "text-[7px] text-gray-400 font-medium";
    const listClass = highlighted ? "text-[7px] text-black/80 space-y-1 pl-1 font-medium" : "text-[7px] text-zinc-400 space-y-1 pl-1";
    const footerClass = highlighted ? "mt-4 pt-2 border-t border-black/10" : "mt-4 pt-2 border-t border-zinc-800";
    const priceClass = highlighted ? "text-xs font-black text-black" : "text-xs font-extrabold text-cofiOlive";
    const buttonClass = highlighted ? "w-full mt-2 bg-black hover:bg-zinc-900 text-[8px] font-bold text-white py-1.5 rounded-lg transition-all uppercase tracking-wider" : "w-full mt-2 bg-[#161616] border border-zinc-800 hover:border-cofiOlive hover:text-cofiOlive text-[8px] font-bold text-white py-1.5 rounded-lg transition-all uppercase tracking-wider";

    return `<div class="${cardClass}"><div class="space-y-2"><div class="flex justify-between items-start"><h4 class="${titleClass}">${escapeHtml(plan.name)}</h4><span class="${durationClass}">${formatDuration(plan.duration_minutes)}</span></div><p class="${textClass}">Ideal para:</p><ul class="${listClass}"><li>• ${escapeHtml(plan.description)}</li></ul></div><div class="${footerClass}"><p class="${priceClass}">${formatPrice(plan.price)}</p><button data-payment-plan-id="${plan.id}" class="${buttonClass}">Seleccionar</button></div></div>`;
}

function renderDesktopPlan(plan, index) {
    const highlighted = index === 2;
    const cardClass = highlighted
        ? "bg-cofiOlive text-black rounded-2xl p-5 flex flex-col justify-between shadow-xl transition-all text-left scale-[1.02] border-2 border-cofiOlive"
        : "bg-cofiCard border border-zinc-900 rounded-2xl p-5 flex flex-col justify-between glow-hover transition-all text-left";
    const titleClass = highlighted ? "text-sm font-black uppercase tracking-wider font-grotesk" : "text-sm font-bold text-white uppercase tracking-wider font-grotesk";
    const durationClass = highlighted ? "text-[9px] bg-black/10 text-black font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider" : "text-[9px] bg-zinc-900 text-gray-400 font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider";
    const textClass = highlighted ? "text-xs text-black/70 font-bold" : "text-xs text-gray-400 font-semibold";
    const listClass = highlighted ? "text-xs text-black/80 space-y-1.5 pl-1.5 font-medium" : "text-xs text-zinc-400 space-y-1.5 pl-1.5";
    const footerClass = highlighted ? "mt-6 pt-3 border-t border-black/10" : "mt-6 pt-3 border-t border-zinc-800";
    const priceClass = highlighted ? "text-lg font-black text-black" : "text-lg font-black text-cofiOlive";
    const buttonClass = highlighted ? "w-full mt-3 bg-black hover:bg-zinc-900 text-[10px] font-bold text-white py-2.5 rounded-xl transition-all uppercase tracking-wider" : "w-full mt-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-cofiOlive hover:text-cofiOlive text-[10px] font-bold text-white py-2.5 rounded-xl transition-all uppercase tracking-wider";

    return `<div class="${cardClass}"><div class="space-y-3"><div class="flex justify-between items-start"><h4 class="${titleClass}">${escapeHtml(plan.name)}</h4><span class="${durationClass}">${formatDuration(plan.duration_minutes)}</span></div><p class="${textClass}">Ideal para:</p><ul class="${listClass}"><li>• ${escapeHtml(plan.description)}</li></ul></div><div class="${footerClass}"><p class="${priceClass}">${formatPrice(plan.price)}</p><button data-payment-plan-id="${plan.id}" class="${buttonClass}">Seleccionar Plan</button></div></div>`;
}

async function cargarPlanes() {
    const mobileContainer = document.getElementById("mobile-plan-list");
    const desktopContainer = document.getElementById("desktop-plan-list");
    if (!mobileContainer || !desktopContainer) return;

    try {
        const plans = await window.CofiApi.getPlans();
        window.CofiPlans = plans;
        mobileContainer.innerHTML = plans.map(renderMobilePlan).join("");
        desktopContainer.innerHTML = plans.map(renderDesktopPlan).join("");
    } catch (error) {
        console.error(error);
        const message = typeof mensajeErrorAmigable === "function"
            ? mensajeErrorAmigable(error, "No fue posible cargar los planes. Intenta nuevamente.")
            : "No fue posible cargar los planes. Intenta nuevamente.";
        mobileContainer.innerHTML = `<p class="text-xs text-zinc-400">${message}</p>`;
        desktopContainer.innerHTML = `<p class="text-xs text-zinc-400">${message}</p>`;
    }
}
