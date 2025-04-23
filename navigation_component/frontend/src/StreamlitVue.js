// Адаптация Streamlit Component API для Vue 3
export const Streamlit = {
    // Streamlit отправит сообщение с данными, которые мы хотим отобразить
    setComponentReady() {
      window.parent.postMessage({ type: "streamlit:componentReady", apiVersion: 1 }, "*");
    },
  
    // Streamlit отправит сообщение с новыми данными
    onDataFromPython(callback) {
      window.addEventListener("message", function(event) {
        if (event.data.type === "streamlit:render") {
          callback(event.data.args);
        }
      });
      this.setComponentReady();
    },
  
    // Отправляем данные обратно в Python
    sendDataToPython(data) {
      window.parent.postMessage({
        type: "streamlit:componentValue",
        value: data,
      }, "*");
    },
  
    // Устанавливаем высоту iframe
    setFrameHeight(height) {
      window.parent.postMessage({
        type: "streamlit:setFrameHeight",
        height: height || document.body.scrollHeight,
      }, "*");
    }
  };
  
  // Экспортируем Streamlit для использования в компонентах Vue
  export default Streamlit;