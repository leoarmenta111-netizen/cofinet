(() => {
    const {
        PIN_OPERATOR,
        SUPER_ADMIN,
        adminRequest,
        confirmAdminAction,
        copyText,
        currentAdmin,
        formatDate,
        formatDuration,
        formatMoney,
        setButtonLoading,
        showEmpty,
        showToast
    } = window.CofiAdmin;

    let activeAdmin = null;
    let latestBatch = null;
    let loadedBatches = [];
    let loadedInternalCredentials = [];
    let batchSubmitting = false;
    const batchPlan = document.getElementById("batch-plan");
    const batchButton = document.getElementById("batch-generate");
    const branchSelect = document.getElementById("branch");

    function selectedBranchCode() {
        return branchSelect?.value || "";
    }

    function selectedBranchName() {
        return branchSelect?.selectedOptions?.[0]?.textContent || "Sucursal";
    }

    function updateBatchAvailability() {
        batchButton.disabled =
            batchPlan.disabled ||
            !batchPlan.value ||
            !selectedBranchCode();
    }

    function requestUuid() {
        if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
        const bytes = crypto.getRandomValues(new Uint8Array(16));
        bytes[6] = (bytes[6] & 0x0f) | 0x40;
        bytes[8] = (bytes[8] & 0x3f) | 0x80;
        const hex = [...bytes].map(value => value.toString(16).padStart(2, "0")).join("");
        return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    }

    function actionButton(label, callback, tone = "button-ghost") {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `button ${tone} button-small`;
        button.textContent = label;
        button.addEventListener("click", callback);
        return button;
    }

    function statusLabel(value) {
        return ({ completed: "Completo", partial: "Parcial", failed: "Fallido", processing: "Procesando" })[value] || value;
    }

    function statusBadge(label, tone) {
        const badge = document.createElement("span");
        badge.className = `badge badge-${tone}`;
        badge.textContent = label;
        return badge;
    }

    async function configureBatchPlans() {
        const plans = await adminRequest("/plans");
        batchPlan.replaceChildren();
        if (!plans.length) {
            batchPlan.add(new Option("No hay planes activos disponibles.", ""));
            batchPlan.disabled = true;
            batchButton.disabled = true;
            return;
        }
        for (const plan of plans) {
            batchPlan.add(new Option(`${plan.name} · ${formatMoney(plan.price)} · ${formatDuration(plan.duration_minutes)}`, plan.id));
        }
        updateBatchAvailability();
    }

    function renderBatchResult(batch) {
        latestBatch = batch;
        document.getElementById("batch-result").hidden = false;
        document.getElementById("batch-requested").textContent = batch.requested;
        document.getElementById("batch-created").textContent = batch.created;
        document.getElementById("batch-failed").textContent = batch.failed;
        document.getElementById("batch-status").textContent = statusLabel(batch.status);
        document.getElementById("batch-print").disabled = !batch.created;
        document.getElementById("batch-csv").disabled = !batch.created;
    }

    function renderBatches(batches) {
        const body = document.getElementById("batch-list");
        body.replaceChildren();
        document.getElementById("batch-history-note").textContent = activeAdmin.role === PIN_OPERATOR
            ? "Solo lotes creados por tu cuenta"
            : "Todos los operadores";
        if (!batches.length) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 8;
            showEmpty(cell, "Aún no hay lotes", "Los lotes confirmados aparecerán aquí para reimpresión.");
            row.append(cell);
            body.append(row);
            return;
        }
        for (const batch of batches) {
            const row = document.createElement("tr");
            const values = [
                batch.batch_uuid.slice(0, 8),
                batch.branch_name || "Sucursal no identificada",
                batch.plan_name,
                `${batch.created}/${batch.requested}`
            ];
            values.forEach((value, index) => {
                const cell = document.createElement("td");
                cell.textContent = value;
                if (index === 0) cell.className = "mono";
                row.append(cell);
            });
            const status = document.createElement("td");
            const statusTone = batch.status === "completed" ? "success" : batch.status === "failed" ? "danger" : "warning";
            status.append(statusBadge(statusLabel(batch.status), statusTone));
            row.append(status);
            for (const value of [batch.created_by_admin_name || "Sin auditoría", formatDate(batch.created_at)]) {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.append(cell);
            }
            const actions = document.createElement("td");
            actions.className = "row-actions";
            actions.append(
                actionButton("Reimprimir", () => printBatchById(batch.id)),
                actionButton("CSV", () => csvBatchById(batch.id))
            );
            row.append(actions);
            body.append(row);
        }
    }

    function renderSelectedBatches() {
        const branchCode = selectedBranchCode();

        const visibleBatches = branchCode
            ? loadedBatches.filter(batch => batch.branch_code === branchCode)
            : loadedBatches;

        renderBatches(visibleBatches);

        document.getElementById("batch-history-note").textContent =
            branchCode
                ? `Sucursal: ${selectedBranchName()}`
                : "Todas las sucursales";
    }

    async function loadBatches() {
        const response = await adminRequest("/admin/pin-batches");
        loadedBatches = response.batches;
        renderSelectedBatches();
    }

    function buildTicket(ticket, { internal = false, branchName = null } = {}) {
        const node = document.createElement("article");
        node.className = "batch-ticket";
        const brand = document.createElement("strong");
        brand.className = "batch-ticket-brand";
        brand.textContent = "CofiNet+";
        const kind = document.createElement("span");
        kind.className = "batch-ticket-kind";
        kind.textContent = internal ? "Acceso interno permanente" : "Acceso WiFi";
        const pin = document.createElement("strong");
        pin.className = "batch-ticket-pin";
        pin.textContent = ticket.pin;
        const details = document.createElement("dl");
        const entries = internal
            ? [
                ["Sucursal", branchName || ticket.branch_name || "—"],
                ["Dispositivo", ticket.label],
                ["Duración", "Permanente"],
                ["Generado", formatDate(ticket.created_at)]
            ]
            : [
                ["Sucursal", branchName || "—"],
                ["Plan", ticket.plan_name],
                ["Duración", formatDuration(ticket.duration_minutes)],
                ["Precio", formatMoney(ticket.amount)],
                ["Generado", formatDate(ticket.issued_at)]
            ];
        for (const [label, value] of entries) {
            const term = document.createElement("dt");
            term.textContent = label;
            const detail = document.createElement("dd");
            detail.textContent = value;
            details.append(term, detail);
        }
        const instruction = document.createElement("p");
        instruction.textContent = internal
            ? "Usa este PIN como usuario y contraseña."
            : "Abre el portal CofiNet+ e ingresa este PIN para activar tu acceso.";
        node.append(brand, kind, pin, details, instruction);
        return node;
    }

    function printTickets(tickets, heading, options = {}) {
        const grid = document.getElementById("batch-ticket-grid");
        grid.replaceChildren(...tickets.map(ticket => buildTicket(ticket, options)));
        document.getElementById("batch-print-heading").textContent = heading;
        document.body.classList.add("printing-batch");
        window.addEventListener("afterprint", () => document.body.classList.remove("printing-batch"), { once: true });
        window.print();
    }

    async function printBatchById(batchId) {
        try {
            const data = await adminRequest(`/admin/pin-batches/${batchId}/print-data`);
            printTickets(
                data.tickets,
                `${data.branch_name} · ${data.plan_name} · ${data.tickets.length} accesos`,
                { branchName: data.branch_name }
            );
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    function downloadBatchCsv(batch) {
        const quote = value => `"${String(value ?? "").replaceAll('"', '""')}"`;
        const rows = [
            ["PIN", "Sucursal", "Plan", "Duración minutos", "Precio MXN", "Generado", "Expira"],
            ...batch.pins.map(pin => [
                pin.pin,
                batch.branch_name,
                pin.plan_name,
                pin.duration_minutes,
                pin.amount,
                pin.issued_at,
                pin.expires_at
            ])
        ];
        const csv = "\ufeff" + rows.map(row => row.map(quote).join(",")).join("\r\n");
        const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
        const link = document.createElement("a");
        link.href = url;
        link.download = `cofinet-lote-${batch.batch_uuid}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    }

    async function csvBatchById(batchId) {
        try {
            downloadBatchCsv(await adminRequest(`/admin/pin-batches/${batchId}`));
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    function permanentBadge() {
        const badge = document.createElement("span");
        badge.className = "badge badge-warning";
        badge.textContent = "Acceso interno permanente";
        return badge;
    }

    function renderInternal(credentials) {
        const body = document.getElementById("internal-list");
        body.replaceChildren();
        if (!credentials.length) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 7;
            showEmpty(cell, "Sin dispositivos registrados", "Genera un acceso permanente para comenzar.");
            row.append(cell);
            body.append(row);
            return;
        }
        for (const credential of credentials) {
            const row = document.createElement("tr");
            for (const value of [
                credential.label,
                credential.branch_name || "Sucursal no identificada",
                credential.pin
            ]) {
                const cell = document.createElement("td");
                cell.textContent = value;
                if (value === credential.pin) cell.className = "mono";
                row.append(cell);
            }
            const type = document.createElement("td");
            type.append(permanentBadge());
            row.append(type);
            const status = document.createElement("td");
            status.append(statusBadge(credential.is_active ? "Activo" : "Deshabilitado", credential.is_active ? "success" : "neutral"));
            row.append(status);
            const created = document.createElement("td");
            created.textContent = formatDate(credential.created_at);
            row.append(created);
            const actions = document.createElement("td");
            actions.className = "row-actions";
            actions.append(
                actionButton("Copiar", () => copyText(credential.pin)),
                actionButton(
                    "Imprimir",
                    () => printTickets(
                        [credential],
                        `${credential.branch_name} · ${credential.label}`,
                        {
                            internal: true,
                            branchName: credential.branch_name
                        }
                    )
                )
            );
            const nextActive = !credential.is_active;
            actions.append(actionButton(
                nextActive ? "Reactivar" : "Deshabilitar",
                () => changeInternalStatus(credential, nextActive),
                nextActive ? "button-secondary" : "button-danger"
            ));
            row.append(actions);
            body.append(row);
        }
    }

    function renderSelectedInternal() {
        const branchCode = selectedBranchCode();

        const visibleCredentials = branchCode
            ? loadedInternalCredentials.filter(
                credential => credential.branch_code === branchCode
            )
            : loadedInternalCredentials;

        renderInternal(visibleCredentials);
    }

    async function loadInternal() {
        const response = await adminRequest("/admin/internal-access");
        loadedInternalCredentials = response.credentials;
        renderSelectedInternal();
    }

    async function changeInternalStatus(credential, isActive) {
        const verb = isActive ? "Reactivar" : "Deshabilitar";
        const confirmed = await confirmAdminAction({
            title: `${verb} acceso`,
            message: `${verb} el acceso de ${credential.label}?`,
            confirmLabel: verb,
            danger: !isActive
        });
        if (!confirmed) return;
        try {
            await adminRequest(`/admin/internal-access/${credential.id}/status`, {
                method: "PATCH",
                body: JSON.stringify({ is_active: isActive })
            });
            await loadInternal();
            showToast("Estado actualizado.", "success");
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    branchSelect?.addEventListener("change", () => {
        updateBatchAvailability();
        renderSelectedBatches();
        renderSelectedInternal();
    });
    batchPlan.addEventListener("change", updateBatchAvailability);
    window.addEventListener("cofinet:branch-changed", updateBatchAvailability);

    document.getElementById("refresh-batches").addEventListener("click", () => {
        loadBatches().catch(error => showToast(error.message, "error"));
    });

    document.getElementById("batch-print").addEventListener("click", () => {
        if (latestBatch) {
            printTickets(
                latestBatch.pins,
                `${latestBatch.branch_name} · ${latestBatch.plan_name} · ${latestBatch.created} accesos`,
                { branchName: latestBatch.branch_name }
            );
        }
    });

    document.getElementById("batch-csv").addEventListener("click", () => {
        if (latestBatch) downloadBatchCsv(latestBatch);
    });

    document.getElementById("batch-form").addEventListener("submit", async event => {
        event.preventDefault();
        const quantity = Number(document.getElementById("batch-quantity").value);
        if (
            !Number.isInteger(quantity) ||
            quantity < 1 ||
            quantity > 100 ||
            !selectedBranchCode() ||
            batchButton.disabled ||
            batchSubmitting
        ) return;
        batchSubmitting = true;
        const confirmed = await confirmAdminAction({
            title: "Confirmar generación por lote",
            message: `Se intentarán crear ${quantity} accesos para ${selectedBranchName()}. Cada PIN se confirmará en MikroTik y PostgreSQL.`,
            confirmLabel: `Generar ${quantity} PINs`
        });
        if (!confirmed) {
            batchSubmitting = false;
            return;
        }

        const progress = document.getElementById("batch-progress");
        const errorNode = document.getElementById("batch-error");
        const requestKey = `${selectedBranchCode()}:${batchPlan.value}:${quantity}`;
        let pendingRequest = null;
        try {
            pendingRequest = JSON.parse(sessionStorage.getItem("cofinet_pending_pin_batch"));
        } catch {
            pendingRequest = null;
        }
        if (!pendingRequest || pendingRequest.key !== requestKey) {
            pendingRequest = { key: requestKey, requestId: requestUuid() };
            sessionStorage.setItem("cofinet_pending_pin_batch", JSON.stringify(pendingRequest));
        }
        errorNode.textContent = "";
        progress.hidden = false;
        document.getElementById("batch-result").hidden = true;
        setButtonLoading(batchButton, true, `Creando ${quantity} accesos…`);
        try {
            latestBatch = await adminRequest("/admin/pin-batches", {
                method: "POST",
                body: JSON.stringify({
                    plan_id: Number(batchPlan.value),
                    branch_code: selectedBranchCode(),
                    quantity,
                    request_id: pendingRequest.requestId
                })
            });
            sessionStorage.removeItem("cofinet_pending_pin_batch");
            renderBatchResult(latestBatch);
            showToast(`${latestBatch.created} PINs confirmados.`, "success");
        } catch (error) {
            if (error.payload?.batch) {
                sessionStorage.removeItem("cofinet_pending_pin_batch");
                latestBatch = error.payload.batch;
                renderBatchResult(latestBatch);
                errorNode.textContent = `${latestBatch.created} confirmados; ${latestBatch.failed} fallidos. Ningún PIN fallido se reportó como creado.`;
            } else {
                errorNode.textContent = error.message;
            }
            showToast(errorNode.textContent, "error");
        } finally {
            progress.hidden = true;
            setButtonLoading(batchButton, false);
            batchSubmitting = false;
            await loadBatches();
        }
    });

    document.getElementById("internal-form").addEventListener("submit", async event => {
        event.preventDefault();
        if (activeAdmin?.role !== SUPER_ADMIN || !selectedBranchCode()) return;
        const labelInput = document.getElementById("internal-label");
        const label = labelInput.value.trim();
        const button = document.getElementById("internal-generate");
        const errorNode = document.getElementById("internal-error");
        const confirmed = await confirmAdminAction({
            title: "Generar acceso permanente",
            message: `Crear una credencial interna sin expiración para ${label} en ${selectedBranchName()}?`,
            confirmLabel: "Generar acceso"
        });
        if (!confirmed) return;
        errorNode.textContent = "";
        setButtonLoading(button, true, "Creando acceso…");
        try {
            const credential = await adminRequest("/admin/internal-access", {
                method: "POST",
                body: JSON.stringify({
                    label,
                    branch_code: selectedBranchCode(),
                    request_id: requestUuid()
                })
            });
            labelInput.value = "";
            await loadInternal();
            await copyText(credential.pin);
            showToast("Acceso interno confirmado y PIN copiado.", "success");
        } catch (error) {
            errorNode.textContent = error.message;
            showToast(error.message, "error");
        } finally {
            setButtonLoading(button, false);
        }
    });

    (async () => {
        activeAdmin = await currentAdmin();
        const tasks = [configureBatchPlans(), loadBatches()];
        if (activeAdmin.role === SUPER_ADMIN) {
            document.getElementById("internal-access-section").hidden = false;
            tasks.push(loadInternal());
        }
        await Promise.all(tasks);
    })().catch(error => showToast(error.message, "error"));
})();
