document.addEventListener('DOMContentLoaded', function() {
    const messagesContainer = document.querySelector('ul.messages');
    if (messagesContainer) {
        const messagesListItems = messagesContainer.querySelectorAll('li');
        
        messagesListItems.forEach(function(messageLi) {
            // A animação CSS já cuida do fade-out e visibility:hidden
            // Este JS vai remover o elemento do DOM após um tempo maior para garantir
            // ou poderia ser usado para adicionar uma classe que faz o display:none
            setTimeout(function() {
                // messageLi.style.display = 'none'; // Esconde o item
                if (messageLi.parentNode) {
                     messageLi.parentNode.removeChild(messageLi); // Remove o item do DOM
                }

                // Verifica se o container de mensagens ficou vazio
                if (messagesContainer.children.length === 0) {
                    messagesContainer.style.display = 'none'; // Esconde o container UL
                }
            }, 4000); // Garante que o item seja removido/escondido após a animação CSS
        });
    }
});



