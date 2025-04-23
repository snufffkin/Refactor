// vue.config.js
module.exports = {
    publicPath: "./",
    // Отключаем хэширование файлов для облегчения интеграции
    filenameHashing: false,
    // Настройка выходной директории
    outputDir: "../navigation_component/frontend/build",
  
    // Отключаем ненужные функции Vue CLI
    productionSourceMap: false,
    configureWebpack: {
      // Для возможности интеграции со Streamlit
      devServer: {
        headers: {
          "Access-Control-Allow-Origin": "*"
        },
        port: 3001,
      },
    },
  };