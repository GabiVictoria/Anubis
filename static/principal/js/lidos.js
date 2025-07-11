  function filtrarAno() {
      const anoSelecionado = document.getElementById("filtro").value;
      const cards = document.querySelectorAll(".livro-card");
      cards.forEach(card => {
        const ano = card.getAttribute("data-ano");
        card.style.display = (anoSelecionado === "Todos" || ano === anoSelecionado) ? "flex" : "none";
      });
    }

    function filtrarCategoria(categoria) {
      const cards = document.querySelectorAll(".livro-card");
      cards.forEach(card => {
        const cardCategoria = card.getAttribute("data-categoria");
        card.style.display = (cardCategoria === categoria) ? "flex" : "none";
      });
    }