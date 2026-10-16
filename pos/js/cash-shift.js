(function (root, factory) {
    const api = factory();

    if (
        typeof module !== "undefined" &&
        module.exports
    ) {
        module.exports = api;
    }

    if (root) {
        root.CofiPosCashShiftModule =
            api;
    }
})(
    typeof window !== "undefined"
        ? window
        : globalThis,
    function () {
        const DENOMINATIONS_CENTS = [
            100,
            200,
            500,
            1000,
            2000,
            5000,
            10000,
            20000,
            50000,
            100000,
        ];

        function createCashShift({
            api,
            staffSession,
            isOnline =
                () =>
                    globalThis
                        .navigator?.onLine
                    !== false,
        }) {
            let currentShift = null;
            let reconciliationState =
                null;

            function requireOnline(
                operation
            ) {
                if (!isOnline()) {
                    throw new Error(
                        `${operation} requiere conexión al servidor`
                    );
                }
            }

            function activeStaff() {
                const staff =
                    staffSession.current();

                if (!staff) {
                    throw new Error(
                        "Desbloquea el POS con tu PIN"
                    );
                }

                return staff;
            }

            function requireManager(
                managerCredentials
            ) {
                if (
                    !managerCredentials ||
                    !Number.isInteger(
                        Number(
                            managerCredentials
                                .staffId
                        )
                    ) ||
                    Number(
                        managerCredentials
                            .staffId
                    ) <= 0 ||
                    typeof managerCredentials
                        .pin !== "string" ||
                    !managerCredentials
                        .pin
                        .trim()
                ) {
                    throw new Error(
                        "Se requiere autorización de Manager"
                    );
                }
            }

            function sanitizeCurrentShift(
                value
            ) {
                if (!value) {
                    return null;
                }

                const sanitized = {
                    ...value,
                };

                [
                    "expected_cash",
                    "expected_total",
                    "difference",
                    "variance",
                    "ledger_total",
                    "cash_ledger_total",
                ].forEach(key => {
                    delete sanitized[key];
                });

                return sanitized;
            }

            function calculateDenominationTotal(
                counts
            ) {
                const cents =
                    (counts || [])
                        .reduce(
                            (
                                sum,
                                item
                            ) => {
                                const denomination =
                                    Number(
                                        item
                                            .denomination_cents
                                    );

                                const quantity =
                                    Number(
                                        item
                                            .quantity
                                    );

                                if (
                                    !DENOMINATIONS_CENTS
                                        .includes(
                                            denomination
                                        ) ||
                                    !Number.isInteger(
                                        quantity
                                    ) ||
                                    quantity <
                                        0
                                ) {
                                    throw new Error(
                                        "Conteo de denominaciones inválido"
                                    );
                                }

                                return (
                                    sum +
                                    (
                                        denomination *
                                        quantity
                                    )
                                );
                            },
                            0
                        );

                return cents / 100;
            }

            async function loadCurrent() {
                const staff =
                    activeStaff();

                const result =
                    await api
                        .getCurrentCashShift(
                            {
                                accessToken:
                                    staff
                                        .access_token,
                            }
                        );

                currentShift =
                    sanitizeCurrentShift(
                        result
                    );

                reconciliationState =
                    result?.status ===
                        "CLOSING" &&
                    result.counted_cash != null &&
                    result.expected_cash != null &&
                    result.difference != null
                        ? {
                            shift_uuid:
                                result.shift_uuid,
                            status:
                                "CLOSING",
                            counted_cash:
                                result.counted_cash,
                            expected_cash:
                                result.expected_cash,
                            difference:
                                result.difference,
                        }
                        : null;

                return currentShift
                    ? {
                        ...currentShift,
                    }
                    : null;
            }

            async function open(
                openingCounts,
                managerCredentials
            ) {
                requireOnline(
                    "Abrir caja"
                );

                requireManager(
                    managerCredentials
                );

                const staff =
                    activeStaff();

                calculateDenominationTotal(
                    openingCounts
                );

                const result =
                    await api
                        .openCashShift(
                            {
                                opening_counts:
                                    openingCounts,
                                authorizing_manager_staff_id:
                                    Number(
                                        managerCredentials
                                            .staffId
                                    ),
                                manager_pin:
                                    managerCredentials
                                        .pin,
                            },
                            {
                                accessToken:
                                    staff
                                        .access_token,
                            }
                        );

                currentShift =
                    sanitizeCurrentShift(
                        result
                    );

                reconciliationState =
                    null;

                return {
                    ...currentShift,
                };
            }

            async function recordMovement(
                payload,
                managerCredentials
            ) {
                requireOnline(
                    "Movimiento de caja"
                );

                requireManager(
                    managerCredentials
                );

                const staff =
                    activeStaff();

                if (
                    !currentShift ||
                    currentShift.status !==
                        "OPEN"
                ) {
                    throw new Error(
                        "La caja no está abierta"
                    );
                }

                if (
                    !payload?.note ||
                    !String(
                        payload.note
                    ).trim()
                ) {
                    throw new Error(
                        "La nota es obligatoria"
                    );
                }

                return api
                    .recordCashMovement(
                        currentShift
                            .shift_uuid,
                        {
                            ...payload,
                            authorizing_manager_staff_id:
                                Number(
                                    managerCredentials
                                        .staffId
                                ),
                            manager_pin:
                                managerCredentials
                                    .pin,
                        },
                        {
                            accessToken:
                                staff
                                    .access_token,
                        }
                    );
            }

            function showReconciliation(
                value
            ) {
                reconciliationState =
                    value
                        ? {
                            ...value,
                        }
                        : null;

                return reconciliationState;
            }

            async function submitClosingCount(
                closingCounts
            ) {
                requireOnline(
                    "Conteo de cierre"
                );

                const staff =
                    activeStaff();

                if (
                    !currentShift ||
                    currentShift.status !==
                        "OPEN"
                ) {
                    throw new Error(
                        "La caja no está abierta"
                    );
                }

                calculateDenominationTotal(
                    closingCounts
                );

                const result =
                    await api
                        .submitCashClosingCount(
                            currentShift
                                .shift_uuid,
                            {
                                closing_counts:
                                    closingCounts,
                            },
                            {
                                accessToken:
                                    staff
                                        .access_token,
                            }
                        );

                currentShift = {
                    ...currentShift,
                    status: "CLOSING",
                };

                return showReconciliation(
                    result
                );
            }

            async function finalizeClose(
                managerCredentials,
                differenceNote = null
            ) {
                requireOnline(
                    "Cerrar caja"
                );

                requireManager(
                    managerCredentials
                );

                const staff =
                    activeStaff();

                if (
                    !reconciliationState
                ) {
                    throw new Error(
                        "Primero realiza el conteo físico de cierre"
                    );
                }

                const difference =
                    Number(
                        reconciliationState
                            .difference
                    );

                if (
                    Number.isFinite(
                        difference
                    ) &&
                    difference !== 0 &&
                    !String(
                        differenceNote ||
                        ""
                    ).trim()
                ) {
                    throw new Error(
                        "Explica la diferencia antes de cerrar"
                    );
                }

                const result =
                    await api
                        .finalizeCashShift(
                            currentShift
                                .shift_uuid,
                            {
                                authorizing_manager_staff_id:
                                    Number(
                                        managerCredentials
                                            .staffId
                                    ),
                                manager_pin:
                                    managerCredentials
                                        .pin,
                                difference_note:
                                    String(
                                        differenceNote ||
                                        ""
                                    ).trim() ||
                                    null,
                            },
                            {
                                accessToken:
                                    staff
                                        .access_token,
                            }
                        );

                currentShift =
                    sanitizeCurrentShift(
                        result
                    );

                reconciliationState =
                    null;

                return {
                    ...currentShift,
                };
            }

            function reconciliation() {
                return reconciliationState
                    ? {
                        ...reconciliationState,
                    }
                    : null;
            }

            function current() {
                return currentShift
                    ? {
                        ...currentShift,
                    }
                    : null;
            }

            return {
                loadCurrent,
                open,
                recordMovement,
                submitClosingCount,
                finalizeClose,
                calculateDenominationTotal,
                showReconciliation,
                reconciliation,
                current,
                denominations:
                    [
                        ...DENOMINATIONS_CENTS,
                    ],
            };
        }

        return {
            createCashShift,
            DENOMINATIONS_CENTS,
        };
    }
);
