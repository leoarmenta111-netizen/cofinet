const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");


function read(path) {
    return fs.readFileSync(
        path,
        "utf8"
    );
}


test(
    "Admin agrega Empleados POS a navegacion de super admin",
    () => {
        const js = read(
            "admin/admin.js"
        );

        assert.ok(
            js.includes(
                '["staff", "staff.html", "Empleados POS"]'
            ),
            "Falta Empleados POS en navegación Admin"
        );
    }
);


test(
    "Admin tiene pagina para administrar empleados POS",
    () => {
        assert.ok(
            fs.existsSync(
                "admin/staff.html"
            ),
            "Falta admin/staff.html"
        );

        if (
            !fs.existsSync(
                "admin/staff.html"
            )
        ) {
            return;
        }

        const html = read(
            "admin/staff.html"
        );

        [
            'data-page="staff"',
            'id="staff-rows"',
            'id="open-create-staff"',
            "Número de empleado",
            "Nombre",
            "Sucursal",
            "Rol",
            "Estado",
            "Acciones",
            '"/admin/pos/staff"',
            "bootstrapAdmin",
            "SUPER_ADMIN",
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Admin permite crear empleado POS",
    () => {
        const html = read(
            "admin/staff.html"
        );

        [
            'id="create-staff-dialog"',
            'id="create-staff-form"',
            'id="new-staff-name"',
            'id="new-staff-branch"',
            'id="new-staff-role"',
            'id="new-staff-pin"',
            'value="CASHIER"',
            'value="MANAGER"',
            '"/branches"',
            'method: "POST"',
            '"/admin/pos/staff"',
            "Nuevo empleado",
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Admin permite editar y activar o desactivar empleado POS",
    () => {
        const html = read(
            "admin/staff.html"
        );

        [
            'id="edit-staff-dialog"',
            'id="edit-staff-form"',
            'id="edit-staff-id"',
            'id="edit-staff-name"',
            'id="edit-staff-role"',
            "Editar",
            "Deshabilitar",
            "Habilitar",
            'method: "PATCH"',
            "/admin/pos/staff/${staff.id}",
            "is_active",
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Admin permite cambiar PIN de empleado POS",
    () => {
        const html = read(
            "admin/staff.html"
        );

        [
            'id="reset-staff-pin-dialog"',
            'id="reset-staff-pin-form"',
            'id="reset-staff-pin-id"',
            'id="reset-staff-pin-value"',
            "Cambiar PIN",
            "/reset-pin",
            'method: "POST"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);
