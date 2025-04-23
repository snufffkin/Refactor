<template>
  <div class="sidebar-menu">
    <div class="section-title">Основные разделы</div>
    <ul class="nav-list">
      <NavigationItem 
        v-for="section in mainSections" 
        :key="section.id"
        :item="section"
        :current-page="currentPage"
        :current-params="currentParams"
        @navigate="navigateTo"
      />
    </ul>
    
    <div class="nav-separator"></div>
    
    <div class="section-title">Структура курсов</div>
    <ul class="nav-list" v-if="programs.length > 0">
      <NavigationItem 
        v-for="program in programs" 
        :key="program.id"
        :item="program"
        :current-page="currentPage"
        :current-params="currentParams"
        @navigate="navigateTo"
      />
    </ul>
    <div class="loading" v-else>
      <div class="loading-spinner"></div>
      <span>Загрузка навигации...</span>
    </div>
  </div>
</template>

<script>
import NavigationItem from './NavigationItem.vue'
import { Streamlit } from './StreamlitVue'

export default {
  name: 'App',
  components: {
    NavigationItem
  },
  data() {
    return {
      navigationData: {
        main_sections: [],
        programs: []
      },
      currentPage: 'overview',
      currentParams: {}
    }
  },
  computed: {
    mainSections() {
      return this.navigationData.main_sections || []
    },
    programs() {
      return this.navigationData.programs || []
    }
  },
  mounted() {
    // Подготавливаем компонент для Streamlit
    Streamlit.onDataFromPython((data) => {
      if (data.navigationData) {
        this.navigationData = data.navigationData
      }
      
      if (data.currentPage) {
        this.currentPage = data.currentPage
      }
      
      if (data.currentParams) {
        this.currentParams = data.currentParams
      }
      
      // Уведомляем Streamlit о готовности компонента
      setTimeout(() => {
        Streamlit.setFrameHeight()
      }, 100)
    })
  },
  methods: {
    navigateTo(url) {
      // Отправляем URL обратно в Python
      Streamlit.sendDataToPython({ action: 'navigate', url })
    }
  }
}
</script>

<style>
/* Общие стили */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
.sidebar-menu {
  width: 100%;
  max-width: 300px;
  font-family: "Source Sans Pro", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.95);
}

/* Стили для списков */
ul.nav-list {
  list-style-type: none;
  margin: 0;
  padding: 0;
}
ul.nav-list ul {
  padding-left: 20px;
  overflow: hidden;
  max-height: 0;
  transition: max-height 0.3s ease-out;
}
ul.nav-list ul.expanded {
  max-height: 1000px;
  transition: max-height 0.5s ease-in;
}

/* Заголовки разделов */
.section-title {
  padding: 10px 10px 5px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  font-size: 16px;
}

/* Разделитель */
.nav-separator {
  height: 1px;
  background-color: rgba(255, 255, 255, 0.1);
  margin: 10px 0;
}

/* Загрузка */
.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: rgba(255, 255, 255, 0.7);
}
.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid #4da6ff;
  border-radius: 50%;
  margin-right: 10px;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Скролл */
::-webkit-scrollbar {
  width: 5px;
}
::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 5px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>