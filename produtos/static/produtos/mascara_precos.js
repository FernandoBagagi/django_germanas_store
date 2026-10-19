"use strict";

// Os últimos dois dígitos são sempre os centavos; vazio não aplica filtro.
function formatar_centavos(valor) {
    const digitos = valor.replace(/\D/g, "").replace(/^0+(?=\d)/, "");
    if (!digitos) return "";
    const preenchido = digitos.padStart(3, "0");
    const inteiro = preenchido.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return `${inteiro},${preenchido.slice(-2)}`;
}

for (const campo of document.querySelectorAll(".moeda")) {
    // URLs anteriores com ponto decimal continuam funcionando.
    if (/^\d+(?:\.\d{1,2})?$/.test(campo.value)) {
        const [inteiro, fracao = ""] = campo.value.split(".");
        campo.value = formatar_centavos(inteiro + fracao.padEnd(2, "0"));
    }
    campo.addEventListener("input", () => {
        campo.value = formatar_centavos(campo.value);
    });
}
