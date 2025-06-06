document.addEventListener('DOMContentLoaded', () => {
    // Carousel animation
    const carouselItems = document.querySelectorAll('.container .carousel .carousel-item'); // Mais específico
    if (carouselItems.length > 0) {
        let carouselIndex = 0;
        setInterval(() => {
            carouselItems[carouselIndex].classList.remove('active');
            carouselIndex = (carouselIndex + 1) % carouselItems.length;
            carouselItems[carouselIndex].classList.add('active');
        }, 3000);
    }

    // Tag selection
    const tagContainer = document.getElementById('tag-container');
    if (tagContainer) {
        tagContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('tag')) {
                e.target.classList.toggle('selected');
                // Aqui você poderia adicionar lógica para coletar as tags selecionadas
                // e colocá-las em um input hidden se fosse enviar ao backend.
            }
        });
    }

    // Add new tag
    const newTagInput = document.getElementById('new-tag');
    if (newTagInput && tagContainer) {
        newTagInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && newTagInput.value.trim() !== '') {
                e.preventDefault(); // Previne submissão do formulário se estiver dentro de um
                const newTag = document.createElement('div');
                newTag.classList.add('tag');
                newTag.textContent = newTagInput.value.trim();
                tagContainer.appendChild(newTag);
                newTagInput.value = '';
            }
        });
    }

    // Recommendations update for members
    const membersSelect = document.getElementById('id_limite_membros'); // ID atualizado
    const recommendationList = document.getElementById('recommendation-list');
    if (membersSelect && recommendationList) {
        // Função para atualizar a recomendação
        const updateRecommendation = () => {
            const value = parseInt(membersSelect.value);
            if (value === 10) {
                recommendationList.innerHTML = '<li>10 membros: intimista</li>';
            } else if (value === 20) {
                recommendationList.innerHTML = '<li>20 membros: discussões animadas</li>';
            } else if (value === 50) {
                recommendationList.innerHTML = '<li>50 membros: grandes eventos</li>';
            } else {
                recommendationList.innerHTML = ''; // Limpa se nenhum valor corresponder
            }
        };
        membersSelect.addEventListener('change', updateRecommendation);
        updateRecommendation(); // Chama na carga inicial da página
    }

    // Image recommendations selection
    const imageRecommendations = document.getElementById('image-recommendations');
    const capaRecomendadaInput = document.getElementById('id_capa_recomendada_selecionada');
    const capaUploadInput = document.getElementById('id_capa_clube');

    if (imageRecommendations && capaRecomendadaInput) {
        imageRecommendations.addEventListener('click', (e) => {
            if (e.target.tagName === 'IMG' && e.target.dataset.src) {
                const currentSelected = imageRecommendations.querySelector('img.selected');
                if (currentSelected && currentSelected !== e.target) {
                    currentSelected.classList.remove('selected');
                }
                e.target.classList.toggle('selected');

                if (e.target.classList.contains('selected')) {
                    capaRecomendadaInput.value = e.target.dataset.src;
                    if (capaUploadInput) capaUploadInput.value = ''; // Limpa upload se recomendada for selecionada
                } else {
                    capaRecomendadaInput.value = ''; // Limpa se desselecionada
                }
                console.log('Capa recomendada selecionada:', capaRecomendadaInput.value);
            }
        });
    }

    if (capaUploadInput && capaRecomendadaInput && imageRecommendations) {
        capaUploadInput.addEventListener('change', () => {
            if (capaUploadInput.files && capaUploadInput.files.length > 0) {
                capaRecomendadaInput.value = '';
                const images = imageRecommendations.querySelectorAll('img.selected');
                images.forEach(img => img.classList.remove('selected'));
                console.log('Upload personalizado, limpando recomendada.');
            }
        });
    }

    // Salvar link da reunião (visual)
    const saveLinkBtn = document.getElementById('save-meeting-link');
    const meetingLinkInput = document.getElementById('meeting-link');
    const savedLinkContainer = document.getElementById('saved-link');
    const meetingLinkDisplay = document.getElementById('meeting-link-display');

    if (saveLinkBtn && meetingLinkInput && savedLinkContainer && meetingLinkDisplay) {
        saveLinkBtn.addEventListener('click', () => {
            const link = meetingLinkInput.value.trim();
            if (link) {
                meetingLinkDisplay.href = link;
                meetingLinkDisplay.textContent = link;
                savedLinkContainer.style.display = 'block';
                // alert('Link salvo com sucesso! (Apenas visual nesta tela)'); // Feedback visual
            } else {
                alert('Por favor, insira um link válido.');
            }
        });
    }
});