function atualizarProgresso() {
    const input = document.getElementById("progressInput");
    const valor = Math.max(0, Math.min(100, parseInt(input.value, 10) || 0));
    
    const barra = document.getElementById("progressBar");
    const texto = document.getElementById("progressText");

    barra.style.width = valor + "%";
    texto.textContent = valor + "% concluído";
  }