(() => {
    "use strict";

    const SETTINGS_BY_BRANCH =
        Object.freeze({
            ixtapa: Object.freeze({
                logo_ref:
                    "./assets/coficenter-ticket-logo.png",

                rfc:
                    "HETA0203028E0",

                fiscal_address:
                    "CARR A LAS PALMAS 1179 E, LAS JUNTAS, JALISCO",

                billing_label:
                    "FACTURACIÓN",

                billing_message:
                    "Escanea el código QR para facturar tu compra",

                billing_url:
                    "https://forms.gle/V6UpN26P8wkSfYtT9",

                billing_qr_ref:
                    "./assets/facturacion-qr.png",
            }),
        });

    function getForBranch(
        branchCode
    ) {
        const normalized =
            String(
                branchCode || ""
            )
                .trim()
                .toLowerCase();

        const settings =
            SETTINGS_BY_BRANCH[
                normalized
            ];

        if (!settings) {
            return null;
        }

        return {
            ...settings,
        };
    }

    window.CofiPosFiscalConfig =
        Object.freeze({
            getForBranch,
        });
})();
