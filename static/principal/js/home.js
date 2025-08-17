
document.addEventListener('DOMContentLoaded', () => {
  const appContainer = document.getElementById('app');

  const banners = [
      { imagem: "p5.jpg", alt: "Promoção de Junho" },
      { imagem: "./banner2.jpg", alt: "Novo Clube chegando" },
      { imagem: "./banner3.jpg", alt: "Desafio de Leitura" },
  ];
});

// Carousel animation
let index = 0;
const items = document.querySelectorAll('.carousel-item');
setInterval(() => {
    items[index].classList.remove('active');
    index = (index + 1) % items.length;
    items[index].classList.add('active');
}, 3000);
