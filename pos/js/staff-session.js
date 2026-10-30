(function (root, factory) {
    const api = factory(root);

    if (
        typeof module !== "undefined" &&
        module.exports
    ) {
        module.exports = api;
    }

    if (root) {
        root.CofiPosStaffSessionModule = api;
    }
})(
    typeof window !== "undefined"
        ? window
        : globalThis,
    function (root) {
        const INACTIVITY_MS =
            5 * 60 * 1000;

        const DEFAULT_ITERATIONS =
            150000;

        function bytesToBase64(bytes) {
            if (
                typeof Buffer !== "undefined"
            ) {
                return Buffer
                    .from(bytes)
                    .toString("base64");
            }

            let binary = "";

            for (const byte of bytes) {
                binary +=
                    String.fromCharCode(byte);
            }

            return root.btoa(binary);
        }

        function base64ToBytes(value) {
            if (
                typeof Buffer !== "undefined"
            ) {
                return new Uint8Array(
                    Buffer.from(
                        value,
                        "base64"
                    )
                );
            }

            const binary =
                root.atob(value);

            const bytes =
                new Uint8Array(
                    binary.length
                );

            for (
                let index = 0;
                index < binary.length;
                index += 1
            ) {
                bytes[index] =
                    binary.charCodeAt(index);
            }

            return bytes;
        }

        function combineBytes(
            first,
            second
        ) {
            const output =
                new Uint8Array(
                    first.length +
                    second.length
                );

            output.set(first, 0);
            output.set(
                second,
                first.length
            );

            return output;
        }

        function constantTimeEqual(
            left,
            right
        ) {
            if (
                left.length !==
                right.length
            ) {
                return false;
            }

            let difference = 0;

            for (
                let index = 0;
                index < left.length;
                index += 1
            ) {
                difference |=
                    left[index] ^
                    right[index];
            }

            return difference === 0;
        }

        function createStaffSession({
            branchCode,
            terminalId,
            api,
            db,
            crypto: suppliedCrypto,
            isOnline =
                () => root.navigator?.onLine
                    !== false,
            getActiveShift =
                async () => null,
            timers = {
                setTimeout:
                    (...args) =>
                        root.setTimeout(
                            ...args
                        ),
                clearTimeout:
                    (...args) =>
                        root.clearTimeout(
                            ...args
                        ),
            },
        }) {
            const cryptoObject =
                suppliedCrypto ||
                root.crypto ||
                globalThis.crypto;

            if (
                !cryptoObject?.subtle ||
                typeof cryptoObject
                    .getRandomValues
                    !== "function"
            ) {
                throw new Error(
                    "Web Crypto is required for POS staff verification"
                );
            }

            const encoder =
                new TextEncoder();

            let activeSession = null;
            let inactivityTimer = null;

            function current() {
                if (!activeSession) {
                    return null;
                }

                return {
                    ...activeSession,
                };
            }

            function clearActivityTimer() {
                if (
                    inactivityTimer !== null
                ) {
                    timers.clearTimeout(
                        inactivityTimer
                    );

                    inactivityTimer = null;
                }
            }

            function lock() {
                clearActivityTimer();

                activeSession = null;

                return null;
            }

            function resetActivityTimer() {
                clearActivityTimer();

                if (!activeSession) {
                    return null;
                }

                inactivityTimer =
                    timers.setTimeout(
                        () => {
                            lock();
                        },
                        INACTIVITY_MS
                    );

                return inactivityTimer;
            }

            function verifierContext(
                staffId
            ) {
                return encoder.encode(
                    `|${terminalId}|${staffId}|${branchCode}|`
                );
            }

            async function deriveVerifier(
                pin,
                salt,
                staffId,
                iterations =
                    DEFAULT_ITERATIONS
            ) {
                const key =
                    await cryptoObject
                        .subtle
                        .importKey(
                            "raw",
                            encoder.encode(
                                String(pin)
                            ),
                            "PBKDF2",
                            false,
                            [
                                "deriveBits",
                            ]
                        );

                const scopedSalt =
                    combineBytes(
                        salt,
                        verifierContext(
                            staffId
                        )
                    );

                const bits =
                    await cryptoObject
                        .subtle
                        .deriveBits(
                            {
                                name:
                                    "PBKDF2",
                                salt:
                                    scopedSalt,
                                iterations,
                                hash:
                                    "SHA-256",
                            },
                            key,
                            256
                        );

                return new Uint8Array(
                    bits
                );
            }

            async function persistVerifier(
                serverSession,
                pin
            ) {
                const salt =
                    new Uint8Array(16);

                cryptoObject
                    .getRandomValues(
                        salt
                    );

                const verifier =
                    await deriveVerifier(
                        pin,
                        salt,
                        serverSession
                            .staff_id
                    );

                const shift =
                    await getActiveShift();

                const record = {
                    schema_version: 1,
                    terminal_id:
                        terminalId,
                    branch_code:
                        branchCode,
                    staff_id:
                        serverSession
                            .staff_id,
                    display_name:
                        serverSession
                            .display_name,
                    role:
                        serverSession.role,
                    active: true,
                    authorized_online_at:
                        new Date()
                            .toISOString(),
                    active_shift_uuid:
                        shift?.status ===
                        "OPEN"
                            ? shift
                                .shift_uuid
                            : null,
                    kdf:
                        "PBKDF2-SHA256",
                    iterations:
                        DEFAULT_ITERATIONS,
                    salt:
                        bytesToBase64(
                            salt
                        ),
                    verifier:
                        bytesToBase64(
                            verifier
                        ),
                };

                await db
                    .putStaffVerifier(
                        record
                    );

                return record;
            }

            async function canUnlockOffline(
                staffId,
                pin
            ) {
                if (isOnline()) {
                    return false;
                }

                const shift =
                    await getActiveShift();

                if (
                    !shift ||
                    shift.status !== "OPEN"
                ) {
                    return false;
                }

                const record =
                    await db
                        .getStaffVerifier(
                            terminalId,
                            staffId
                        );

                if (
                    !record ||
                    record.active !== true ||
                    record.terminal_id !==
                        terminalId ||
                    record.branch_code !==
                        branchCode ||
                    record.staff_id !==
                        staffId ||
                    !record.salt ||
                    !record.verifier
                ) {
                    return false;
                }

                if (
                    record
                        .active_shift_uuid &&
                    record
                        .active_shift_uuid !==
                        shift.shift_uuid
                ) {
                    return false;
                }

                const salt =
                    base64ToBytes(
                        record.salt
                    );

                const expected =
                    base64ToBytes(
                        record.verifier
                    );

                const actual =
                    await deriveVerifier(
                        pin,
                        salt,
                        staffId,
                        Number(
                            record
                                .iterations ||
                            DEFAULT_ITERATIONS
                        )
                    );

                return constantTimeEqual(
                    expected,
                    actual
                );
            }

            async function unlock(
                staffId,
                pin
            ) {
                const normalizedStaffId =
                    Number(staffId);

                if (
                    !Number.isInteger(
                        normalizedStaffId
                    ) ||
                    normalizedStaffId <= 0
                ) {
                    throw new Error(
                        "Empleado inválido"
                    );
                }

                if (
                    typeof pin !==
                        "string" ||
                    !pin.trim()
                ) {
                    throw new Error(
                        "PIN requerido"
                    );
                }

                if (isOnline()) {
                    let serverSession;

                    try {
                        serverSession =
                            await api
                                .unlockStaff(
                                    normalizedStaffId,
                                    pin,
                                    {
                                        branchCode,
                                        terminalId,
                                    }
                                );
                    } catch (error) {
                        if (
                            error?.status === 401 ||
                            error?.status === 403
                        ) {
                            await db
                                .deleteStaffVerifier(
                                    terminalId,
                                    normalizedStaffId
                                );
                        }

                        throw error;
                    }

                    await persistVerifier(
                        serverSession,
                        pin
                    );

                    activeSession = {
                        ...serverSession,
                        offline: false,
                    };

                    resetActivityTimer();

                    return current();
                }

                const allowed =
                    await canUnlockOffline(
                        normalizedStaffId,
                        pin
                    );

                if (!allowed) {
                    throw new Error(
                        "Este empleado no puede desbloquear esta terminal sin conexión"
                    );
                }

                const cached =
                    await db
                        .getStaffVerifier(
                            terminalId,
                            normalizedStaffId
                        );

                activeSession = {
                    staff_id:
                        cached.staff_id,
                    display_name:
                        cached
                            .display_name,
                    role:
                        cached.role,
                    branch_code:
                        cached
                            .branch_code,
                    terminal_id:
                        terminalId,
                    offline: true,
                };

                resetActivityTimer();

                return current();
            }

            return {
                unlock,
                lock,
                current,
                resetActivityTimer,
                canUnlockOffline,
                inactivityMs:
                    INACTIVITY_MS,
            };
        }

        return {
            createStaffSession,
            INACTIVITY_MS,
        };
    }
);
