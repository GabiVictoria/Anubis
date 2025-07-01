document.addEventListener('DOMContentLoaded', () => {
  const messagesContainer = document.querySelector('ul.messages');
  if (!messagesContainer) return;

  const messages = messagesContainer.querySelectorAll('li');

  messages.forEach(message => {
    message.addEventListener('animationend', () => {
      message.remove();
      
      if (messagesContainer.children.length === 0) {
        messagesContainer.remove();
      }
    });
  });
});