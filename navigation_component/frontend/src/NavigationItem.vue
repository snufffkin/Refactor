<template>
  <li class="nav-item">
    <div 
      :class="['nav-link-container', isActive ? 'active' : '']"
    >
      <a 
        :href="item.url" 
        class="nav-link"
        @click.prevent="$emit('navigate', item.url)"
      >
        <span v-if="item.icon" class="icon">{{ item.icon }}</span>
        <span v-else class="nav-circle" :class="getCircleClass"></span>
        <span :class="['nav-page-name', isActive ? 'active' : '']" v-html="formatName(item.name)"></span>
      </a>
      
      <div 
        v-if="hasChildren" 
        class="nav-accordion"
        @click.stop="toggleExpanded"
      >
        <span :class="['nav-accordion-icon', isExpanded ? 'close' : 'open']">
          {{ isExpanded ? '✕' : '+' }}
        </span>
      </div>
    </div>
    
    <ul v-if="hasChildren" :class="['nav-list', isExpanded ? 'expanded' : '']">
      <NavigationItem 
        v-for="child in getChildren" 
        :key="child.id"
        :item="child"
        :current-page="currentPage"
        :current-params="currentParams"
        @navigate="$emit('navigate', $event)"
      />
      
      <!-- Отображение дополнительных скрытых карточек -->
      <li v-if="item.has_more_cards" class="nav-item">
        <div class="nav-link-container">
          <span class="nav-link">
            <span class="nav-circle blue"></span>
            <span class="nav-page-name" style="color: rgba(255, 255, 255, 0.5);">
              ...ещё {{ item.more_cards_count }} карточек
            </span>
          </span>
        </div>
      </li>
    </ul>
  </li>
</template>

<script>
export default {
  name: 'NavigationItem',
  props: {
    item: {
      type: Object,
      required: true
    },
    currentPage: {
      type: String,
      default: ''
    },
    currentParams: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      isExpanded: false
    }
  },
  computed: {
    hasChildren() {
      return !!(this.item.children || this.item.modules || this.item.lessons || 
                this.item.groups || (this.item.cards && this.item.cards.length))
    },
    getChildren() {
      return this.item.children || this.item.modules || this.item.lessons || 
             this.item.groups || this.item.cards || []
    },
    isActive() {
      if (this.item.id === this.currentPage) {
        return true
      }
      
      // Проверка на соответствие программе, модулю, уроку и т.д.
      if (this.currentParams) {
        if (this.currentParams.program === this.item.id) return true
        if (this.currentParams.module === this.item.id) return true
        if (this.currentParams.lesson === this.item.id) return true
        if (this.currentParams.gz === this.item.id) return true
        if (this.currentParams.card_id === this.item.id) return true
      }
      
      return false
    },
    getCircleClass() {
      // Определение класса круга на основе риска для карточки
      if (this.item.risk) {
        if (this.item.risk > 0.75) return 'red'
        if (this.item.risk > 0.5) return 'orange'
        if (this.item.risk > 0.25) return 'green'
      }
      return 'blue'
    }
  },
  created() {
    // Автоматически раскрываем элемент, если он активен
    this.isExpanded = this.isActive || this.hasActiveChild()
  },
  methods: {
    toggleExpanded() {
      this.isExpanded = !this.isExpanded
    },
    hasActiveChild() {
      // Проверяем есть ли активные дочерние элементы
      const children = this.getChildren
      
      if (!children.length) return false
      
      return children.some(child => {
        // Проверяем соответствие параметрам URL
        if (child.id === this.currentPage) return true
        if (this.currentParams.program === child.id) return true
        if (this.currentParams.module === child.id) return true
        if (this.currentParams.lesson === child.id) return true
        if (this.currentParams.gz === child.id) return true
        if (this.currentParams.card_id === child.id) return true
        
        return false
      })
    },
    formatName(name) {
      if (!name) return ''
      
      // Форматирование длинных названий с добавлением возможности переноса
      if (name.length > 60) {
        let result = '';
        let charCount = 0;
        
        for (let i = 0; i < name.length; i++) {
          result += name[i];
          charCount++;
          
          if (charCount >= 60 && i < name.length - 1) {
            if (!/[\s.,]/.test(name[i+1])) {
              result += '<wbr>'; // Используем wbr для возможности переноса
            }
            charCount = 0;
          }
          
          if (/[\s.,]/.test(name[i])) {
            charCount = 0;
          }
        }
        
        return result;
      }
      
      return name;
    }
  }
}
</script>

<style>
.nav-item {
  margin: 2px 0;
}
.nav-link-container {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.nav-link-container:hover {
  background-color: rgba(255, 255, 255, 0.1);
}
.nav-link-container.active {
  background-color: rgba(77, 166, 255, 0.2);
}
.nav-link {
  display: flex;
  align-items: flex-start;
  flex-grow: 1;
  text-decoration: none;
  color: rgba(255, 255, 255, 0.9);
}
.nav-circle {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  margin-top: 5px;
}
.nav-circle.blue {
  background-color: #4da6ff;
}
.nav-circle.green {
  background-color: #09ab3b;
}
.nav-circle.orange {
  background-color: #ff8f00;
}
.nav-circle.red {
  background-color: #ff4b4b;
}
.nav-page-name {
  flex-grow: 1;
  white-space: normal;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  overflow: hidden;
  line-height: 1.4;
}
.nav-page-name.active {
  font-weight: 600;
}
.nav-accordion {
  cursor: pointer;
  margin-left: 8px;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}
.nav-accordion:hover {
  background-color: rgba(255, 255, 255, 0.1);
}
.nav-accordion-icon {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.6);
  transition: transform 0.3s;
}
.nav-accordion-icon.open {
  transform: rotate(0deg);
}
.nav-accordion-icon.close {
  transform: rotate(45deg);
}

.icon {
  margin-right: 8px;
  font-size: 16px;
  margin-top: 2px;
}
</style>