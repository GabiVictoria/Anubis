
document.addEventListener('DOMContentLoaded', () => {
  const appContainer = document.getElementById('app');

  const banners = [
      { imagem: "p5.jpg", alt: "Promoção de Junho" },
      { imagem: "./banner2.jpg", alt: "Novo Clube chegando" },
      { imagem: "./banner3.jpg", alt: "Desafio de Leitura" },
  ];

  const clubesUsuario = [
      {
          nome: "Clube dos Sombrios",
          criador: "Ana Silva",
          fundada: "Jan 2023",
          membros: 120,
          imagem: "img/sobrio.jpg",
      },
      {
          nome: "Mistério e Suspense",
          criador: "Carlos Mendes",
          fundada: "Mar 2022",
          membros: 85,
          imagem: "img/Clube1.jpg",
      },
      {
          nome: "Histórias Reais",
          criador: "Fernanda Lopes",
          fundada: "Ago 2021",
          membros: 60,
          imagem: "img/pessoa.jpg",
      },
      {
          nome: "Romances",
          criador: "João Pedro",
          fundada: "Jul 2023",
          membros: 200,
          imagem: "img/Romance.jpg",
      },
      {
          nome: "Clássicos dos Clássicos",
          criador: "Marcos Dias",
          fundada: "Out 2022",
          membros: 150,
          imagem: "img/Sonata.jpg",
      },
      {
          nome: "Aventura",
          criador: "Sofia Martins",
          fundada: "Mai 2023",
          membros: 95,
          imagem: "img/fantasia.jpg",
      },
  ];

  
  const recomendacoes = [
      {
          nome: "Clássicos Modernos",
          dataCriacao: "Fev 2021",
          publico: true,
          criador: "Mariana Rocha",
          livroAtual: "1984 - George Orwell",
      },
      {
          nome: "Sci-Fi Lovers",
          dataCriacao: "Mai 2022",
          publico: false,
          criador: "Lucas Pereira",
          livroAtual: "Duna - Frank Herbert",
      },
      {
          nome: "Literatura Brasileira",
          dataCriacao: "Set 2020",
          publico: true,
          criador: "Paula Lima",
          livroAtual: "Dom Casmurro - Machado de Assis",
      },
      {
          nome: "Ficção Histórica",
          dataCriacao: "Nov 2019",
          publico: false,
          criador: "Ricardo Alves",
          livroAtual: "A Guerra Não Tem Rosto de Mulher",
      },
      {
          nome: "Poesia Contemporânea",
          dataCriacao: "Jan 2024",
          publico: true,
          criador: "Beatriz Nunes",
          criador: "Beatriz Nunes",
          livroAtual: "Alguma Poesia - Drummond",
      },
  ];



  // --- Renderização de "Meus Clubes do Livro" ---
  const myClubsTitle = document.createElement('h1');
  myClubsTitle.className = "text-4xl font-bold";
  myClubsTitle.textContent = "Meus Clubes do Livro";
  appContainer.appendChild(myClubsTitle);

  const myClubsGrid = document.createElement('div');
  myClubsGrid.className = "grid grid-cols-1 md:grid-cols-2 gap-4";
  clubesUsuario.forEach(clube => {
      const card = document.createElement('div');
      card.className = "card flex space-x-4 p-4";

      const img = document.createElement('img');
      img.src = clube.imagem;
      img.alt = clube.nome;
      img.className = "w-24 h-24 object-cover rounded-xl";
      card.appendChild(img);

      const cardContent = document.createElement('div');
      cardContent.className = "card-content flex flex-col justify-between";

      const textDiv = document.createElement('div');
      const h2 = document.createElement('h2');
      h2.className = "text-xl font-semibold";
      h2.textContent = clube.nome;
      const pCriador = document.createElement('p');
      pCriador.className = "text-sm text-gray-600";
      pCriador.textContent = `Fundado por ${clube.criador}`;
      const pFundada = document.createElement('p');
      pFundada.className = "text-xs text-gray-500";
      pFundada.textContent = `Desde ${clube.fundada}`;
      textDiv.appendChild(h2);
      textDiv.appendChild(pCriador);
      textDiv.appendChild(pFundada);
      cardContent.appendChild(textDiv);

      const pMembros = document.createElement('p');
      pMembros.className = "text-sm font-medium";
      pMembros.textContent = `Membros: ${clube.membros}`;
      cardContent.appendChild(pMembros);

      card.appendChild(cardContent);
      myClubsGrid.appendChild(card);
  });
  appContainer.appendChild(myClubsGrid);

  // --- Renderização de "Leituras Atuais" ---
  const currentReadsSection = document.createElement('div');
  currentReadsSection.className = "mt-8";

  const currentReadsTitle = document.createElement('h2');
  currentReadsTitle.className = "text-3xl font-bold mb-4";
  currentReadsTitle.textContent = "Leituras Atuais";
  currentReadsSection.appendChild(currentReadsTitle);

  const currentReadsGrid = document.createElement('div');
  currentReadsGrid.className = "grid grid-cols-1 md:grid-cols-2 gap-4";
  leiturasAtuais.forEach(leitura => {
      const itemDiv = document.createElement('div');
      itemDiv.className = "bg-white p-4 rounded-xl shadow-md flex space-x-4";

      const img = document.createElement('img');
      img.src = leitura.imagem;
      img.alt = leitura.livro;
      img.className = "w-16 h-24 object-cover rounded";
      itemDiv.appendChild(img);

      const contentDiv = document.createElement('div');
      contentDiv.className = "flex flex-col flex-grow";

      const pLivro = document.createElement('p');
      pLivro.className = "text-lg font-semibold mb-2";
      pLivro.textContent = leitura.livro;
      contentDiv.appendChild(pLivro);

      const progressContainer = document.createElement('div');
      progressContainer.className = "progress-container h-4 rounded";
      const progressBar = document.createElement('div');
      progressBar.className = "progress-bar rounded";
      progressBar.style.width = `${leitura.progresso}%`;
      progressContainer.appendChild(progressBar);
      contentDiv.appendChild(progressContainer);

      const pProgresso = document.createElement('p');
      pProgresso.className = "text-right text-sm mt-1";
      pProgresso.textContent = `${leitura.progresso}% concluído`;
      contentDiv.appendChild(pProgresso);

      itemDiv.appendChild(contentDiv);
      currentReadsGrid.appendChild(itemDiv);
  });
  currentReadsSection.appendChild(currentReadsGrid);
  appContainer.appendChild(currentReadsSection);

  // --- Renderização de "Recomendações de Clubes" ---
  const recommendationsSection = document.createElement('div');
  recommendationsSection.className = "mt-8";

  const recommendationsTitle = document.createElement('h2');
  recommendationsTitle.className = "text-3xl font-bold mb-4";
  recommendationsTitle.textContent = "Recomendações de Clubes";
  recommendationsSection.appendChild(recommendationsTitle);

  const recommendationsScroll = document.createElement('div');
  recommendationsScroll.className = "flex space-x-4 overflow-x-auto pb-2";
  recomendacoes.forEach(reco => {
      const card = document.createElement('div');
      card.className = "card min-w-[250px] p-4 flex-shrink-0";

      const cardContent = document.createElement('div');
      cardContent.className = "card-content space-y-2"; 

      const h3 = document.createElement('h3');
      h3.className = "text-lg font-semibold";
      h3.textContent = reco.nome;
      cardContent.appendChild(h3);

      const pDataCriacao = document.createElement('p');
      pDataCriacao.className = "text-xs text-gray-500";
      pDataCriacao.textContent = `Criado em ${reco.dataCriacao}`;
      cardContent.appendChild(pDataCriacao);

      const pCriador = document.createElement('p');
      pCriador.className = "text-xs text-gray-500";
      pCriador.textContent = `Fundador: ${reco.criador}`;
      cardContent.appendChild(pCriador);

      const pLivroAtual = document.createElement('p');
      pLivroAtual.className = "text-sm font-medium";
      pLivroAtual.textContent = `Livro atual: ${reco.livroAtual}`;
      cardContent.appendChild(pLivroAtual);

      const buttonDiv = document.createElement('div');
      buttonDiv.className = "mt-2";
      const button = document.createElement('button');
      button.className = "button w-full rounded-none";
      button.textContent = reco.publico ? "Entrar" : "Solicitar";
      buttonDiv.appendChild(button);
      cardContent.appendChild(buttonDiv);

      card.appendChild(cardContent);
      recommendationsScroll.appendChild(card);
  });
  recommendationsSection.appendChild(recommendationsScroll);
  appContainer.appendChild(recommendationsSection);
});


        // Carousel animation
        let index = 0;
        const items = document.querySelectorAll('.carousel-item');
        setInterval(() => {
            items[index].classList.remove('active');
            index = (index + 1) % items.length;
            items[index].classList.add('active');
        }, 3000);

  