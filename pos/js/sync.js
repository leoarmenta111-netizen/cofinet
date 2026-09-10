window.CofiPosSync = (() => {
    let running = false;

    async function enqueueOrder(payload, localTotal) {
        const now = new Date().toISOString();

        const localOrder = {
            order_uuid: payload.order_uuid,
            payload,
            local_total: localTotal,
            sync_status: "PENDING_SYNC",
            created_at: now,
        };

        const syncEvent = {
            event_uuid: payload.order_uuid,
            event_type: "ORDER_CREATED",
            payload,
            sync_status: "PENDING_SYNC",
            attempts: 0,
            last_error: null,
            created_at: now,
        };

        if (
            payload.receipt_snapshot &&
            payload.folio
        ) {
            localOrder.folio =
                payload.folio;

            localOrder.receipt_snapshot =
                payload.receipt_snapshot;

            await window.CofiPosDB
                .finalizePaidSale({
                    order_uuid:
                        payload.order_uuid,

                    local_order:
                        localOrder,

                    receipt_snapshot:
                        payload.receipt_snapshot,

                    sync_event:
                        syncEvent,
                });

            return;
        }

        await window.CofiPosDB.put(
            "local_orders",
            localOrder
        );

        await window.CofiPosDB.put(
            "sync_queue",
            syncEvent
        );
    }

    async function syncPending() {
        if (running || !navigator.onLine) {
            return;
        }

        running = true;

        try {
            const events =
                await window.CofiPosDB.getPendingEvents();

            for (const event of events) {
                try {
                    // Recover orders created by an older POS build
                    // that accidentally stored terminal_id as null.
                    if (
                        !event.payload?.terminal_id &&
                        event.payload?.branch_code
                    ) {
                        const terminalId =
                            await window.CofiPosDB
                                .getOrCreateTerminalId(
                                    event.payload.branch_code
                                );

                        event.payload.terminal_id =
                            terminalId;

                        await window.CofiPosDB.put(
                            "sync_queue",
                            event
                        );

                        console.log(
                            "Venta pendiente reparada:",
                            event.event_uuid,
                            terminalId
                        );
                    }

                    const response =
                        await window.CofiPosAPI.createOrder(
                            event.payload
                        );

                    await window.CofiPosDB.put(
                        "local_orders",
                        {
                            order_uuid:
                                event.payload.order_uuid,

                            folio:
                                event.payload.folio ||
                                null,

                            receipt_snapshot:
                                event.payload
                                    .receipt_snapshot ||
                                null,

                            payload:
                                event.payload,

                            server_response:
                                response,

                            sync_status:
                                "SYNCED",

                            created_at:
                                event.created_at,

                            synced_at:
                                new Date().toISOString(),
                        }
                    );

                    await window.CofiPosDB.put(
                        "sync_queue",
                        {
                            ...event,
                            sync_status: "SYNCED",
                            attempts:
                                (event.attempts || 0) + 1,
                            last_error: null,
                            synced_at:
                                new Date().toISOString(),
                        }
                    );

                } catch (error) {
                    await window.CofiPosDB.put(
                        "sync_queue",
                        {
                            ...event,
                            attempts:
                                (event.attempts || 0) + 1,
                            last_error: error.message,
                        }
                    );
                }
            }

        } finally {
            running = false;
        }
    }

    return {
        enqueueOrder,
        syncPending,
    };
})();
