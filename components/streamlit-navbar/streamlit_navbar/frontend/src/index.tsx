import "./index.css"
import { Streamlit, RenderData } from "streamlit-component-lib"

// Создаем контейнер для боковой панели навигации
const sidebar = document.body.appendChild(document.createElement("div"))
sidebar.className = "sidebar-menu"

// Заголовок основных разделов
const mainTitle = document.createElement("div")
mainTitle.className = "section-title"
mainTitle.textContent = "Основные разделы"
sidebar.appendChild(mainTitle)

// Список основных разделов
const mainNav = document.createElement("ul")
mainNav.className = "nav-list"
mainNav.id = "main-nav"
sidebar.appendChild(mainNav)

// Изначальный индикатор загрузки
const loader = document.createElement("div")
loader.className = "loading"
loader.innerHTML = '<div class="loading-spinner"></div><span>Загрузка навигации...</span>'
mainNav.appendChild(loader)

// Разделитель
const sep1 = document.createElement("div")
sep1.className = "nav-separator"
sidebar.appendChild(sep1)

// Заголовок структуры курсов
const coursesTitle = document.createElement("div")
coursesTitle.className = "section-title"
coursesTitle.textContent = "Структура курсов"
sidebar.appendChild(coursesTitle)

// Список курсов
const coursesNav = document.createElement("ul")
coursesNav.className = "nav-list"
coursesNav.id = "courses-nav"
sidebar.appendChild(coursesNav)

// Второй разделитель
const sep2 = document.createElement("div")
sep2.className = "nav-separator"
sidebar.appendChild(sep2)

/**
 * Вставляет <wbr> для переноса длинных имен
 */
function formatLongName(name: string, maxLength = 60): string {
  if (!name || name.length <= maxLength) return name
  let result = ""
  let charCount = 0
  for (let i = 0; i < name.length; i++) {
    result += name[i]
    charCount++
    if (charCount >= maxLength && i < name.length - 1) {
      if (!/[\s.,]/.test(name[i + 1])) {
        result += '<wbr>'
      }
      charCount = 0
    }
    if (/[\s.,]/.test(name[i])) {
      charCount = 0
    }
  }
  return result
}

/**
 * Читает параметры из URL
 */
function getUrlParams(): Record<string, string> {
  const params: Record<string, string> = {}
  const searchParams = new URLSearchParams(window.parent.location.search)
  searchParams.forEach((value, key) => {
    params[key] = value
  })
  return params
}

/**
 * Универсальная функция раскрытия/сворачивания подменю:
 * ищет следующий UL-сосед от аккордеон-элемента.
 */
function toggleSubmenu(accordionEl: HTMLElement): void {
  const submenu = accordionEl.parentElement?.nextElementSibling as HTMLElement | null;
  if (!submenu || submenu.tagName !== "UL") return;
  const icon = accordionEl.querySelector(".nav-accordion-icon") as HTMLElement | null;
  const isExpanded = submenu.classList.contains("expanded");
  if (isExpanded) {
    submenu.classList.remove("expanded");
    if (icon) {
      icon.classList.replace("close", "open");
      icon.textContent = "+";
    }
  } else {
    submenu.classList.add("expanded");
    if (icon) {
      icon.classList.replace("open", "close");
      icon.textContent = "✕";
    }
  }
  Streamlit.setFrameHeight();
}

/**
 * Генерирует навигацию из объекта данных
 */
function generateNavigation(data: any): void {
  const currentParams = getUrlParams()
  const currentPage = currentParams.page || "overview"

  // Очищаем списки
  mainNav.innerHTML = ""
  coursesNav.innerHTML = ""

  // Основные разделы
  if (data.main_sections && data.main_sections.length > 0) {
    data.main_sections.forEach((section: any) => {
      const isActive = currentPage === section.id
      const li = document.createElement("li")
      li.className = "nav-item"

      const container = document.createElement("div")
      container.className = `nav-link-container${isActive ? " active" : ""}`
      container.id = `nav-${section.id}`

      const link = document.createElement("a")
      link.href = section.url
      link.className = "nav-link"
      link.target = "_parent"
      link.innerHTML = `
        <span class="icon">${section.icon}</span>
        <span class="nav-page-name${isActive ? " active" : ""}">${section.name}</span>
      `

      container.appendChild(link)
      li.appendChild(container)
      mainNav.appendChild(li)
    })
  } else {
    const noData = document.createElement("div")
    noData.className = "loading"
    noData.textContent = "Нет данных о разделах"
    mainNav.appendChild(noData)
  }

  // Структура курсов
  if (data.programs && data.programs.length > 0) {
    data.programs.forEach((program: any) => {
      const progKey = program.id.replace(/\s+/g, "-").toLowerCase()
      const isActiveProg = currentParams.program === program.id
      const programLi = document.createElement("li")
      programLi.className = "nav-item"

      const progCont = document.createElement("div")
      progCont.className = `nav-link-container${isActiveProg ? " active" : ""}`

      const progLink = document.createElement("a")
      progLink.href = program.url
      progLink.className = "nav-link"
      progLink.target = "_parent"
      progLink.innerHTML = `
        <span class="icon">📚</span>
        <span class="nav-page-name${isActiveProg ? " active" : ""}">${formatLongName(program.name)}</span>
      `
      progCont.appendChild(progLink)

      const progAccordion = document.createElement("div")
      progAccordion.className = "nav-accordion"
      progAccordion.onclick = function(e) {
        e.preventDefault()
        e.stopPropagation()
        toggleSubmenu(progAccordion)
      }
      const progIcon = document.createElement("span")
      progIcon.className = `nav-accordion-icon ${program.modules && program.modules.length > 0 ? "open" : ""}`
      progIcon.textContent = program.modules && program.modules.length > 0 ? "+" : ""
      progAccordion.appendChild(progIcon)
      progCont.appendChild(progAccordion)

      programLi.appendChild(progCont)

      const modulesUl = document.createElement("ul")
      modulesUl.className = "nav-list"
      modulesUl.id = `program-${progKey}-submenu`
      if (isActiveProg) {
        modulesUl.classList.add("expanded")
        progIcon.classList.replace("open", "close")
        progIcon.textContent = "✕"
      }

      if (program.modules) {
        program.modules.forEach((mod: any) => {
          const modKey = mod.id.replace(/\s+/g, "-").toLowerCase()
          const isActiveMod = isActiveProg && currentParams.module === mod.id
          const modLi = document.createElement("li")
          modLi.className = "nav-item"

          const modCont = document.createElement("div")
          modCont.className = `nav-link-container${isActiveMod ? " active" : ""}`
          const modLink = document.createElement("a")
          modLink.href = mod.url
          modLink.className = "nav-link"
          modLink.target = "_parent"
          modLink.innerHTML = `
            <span class="nav-circle blue"></span>
            <span class="nav-page-name${isActiveMod ? " active" : ""}">${formatLongName(mod.name)}</span>
          `
          modCont.appendChild(modLink)

          const modAccordion = document.createElement("div")
          modAccordion.className = "nav-accordion"
          modAccordion.onclick = function(e) {
            e.preventDefault()
            e.stopPropagation()
            toggleSubmenu(modAccordion)
          }
          const modIcon = document.createElement("span")
          modIcon.className = `nav-accordion-icon ${mod.lessons && mod.lessons.length > 0 ? "open" : ""}`
          modIcon.textContent = mod.lessons && mod.lessons.length > 0 ? "+" : ""
          modAccordion.appendChild(modIcon)
          modCont.appendChild(modAccordion)

          modLi.appendChild(modCont)

          const lessonsUl = document.createElement("ul")
          lessonsUl.className = "nav-list"
          lessonsUl.id = `module-${progKey}-${modKey}-submenu`
          if (isActiveMod) {
            lessonsUl.classList.add("expanded")
            modIcon.classList.replace("open", "close")
            modIcon.textContent = "✕"
          }

          if (mod.lessons) {
            mod.lessons.forEach((les: any) => {
              const lesKey = les.id.replace(/\s+/g, "-").toLowerCase()
              const isActiveLes = isActiveMod && currentParams.lesson === les.id
              const lesLi = document.createElement("li")
              lesLi.className = "nav-item"

              const lesCont = document.createElement("div")
              lesCont.className = `nav-link-container${isActiveLes ? " active" : ""}`
              const lesLink = document.createElement("a")
              lesLink.href = les.url
              lesLink.className = "nav-link"
              lesLink.target = "_parent"
              lesLink.innerHTML = `
                <span class="nav-circle blue"></span>
                <span class="nav-page-name${isActiveLes ? " active" : ""}">${les.name}</span>
              `
              lesCont.appendChild(lesLink)

              const lesAccordion = document.createElement("div")
              lesAccordion.className = "nav-accordion"
              lesAccordion.onclick = function(e) {
                e.preventDefault()
                e.stopPropagation()
                toggleSubmenu(lesAccordion)
              }
              const lesIcon = document.createElement("span")
              lesIcon.className = `nav-accordion-icon ${les.groups && les.groups.length > 0 ? "open" : ""}`
              lesIcon.textContent = les.groups && les.groups.length > 0 ? "+" : ""
              lesAccordion.appendChild(lesIcon)
              lesCont.appendChild(lesAccordion)

              lesLi.appendChild(lesCont)

              const groupsUl = document.createElement("ul")
              groupsUl.className = "nav-list"
              groupsUl.id = `lesson-${progKey}-${modKey}-${lesKey}-submenu`
              if (isActiveLes) {
                groupsUl.classList.add("expanded")
                lesIcon.classList.replace("open", "close")
                lesIcon.textContent = "✕"
              }

              if (les.groups) {
                les.groups.forEach((grp: any) => {
                  const grpKey = grp.id.replace(/\s+/g, "-").toLowerCase()
                  const isActiveGrp = isActiveLes && currentParams.gz === grp.id
                  const grpLi = document.createElement("li")
                  grpLi.className = "nav-item"

                  const grpCont = document.createElement("div")
                  grpCont.className = `nav-link-container${isActiveGrp ? " active" : ""}`
                  const grpLink = document.createElement("a")
                  grpLink.href = grp.url
                  grpLink.className = "nav-link"
                  grpLink.target = "_parent"
                  grpLink.innerHTML = `
                    <span class="nav-circle blue"></span>
                    <span class="nav-page-name${isActiveGrp ? " active" : ""}">${grp.name}</span>
                  `
                  grpCont.appendChild(grpLink)

                  const grpAccordion = document.createElement("div")
                  grpAccordion.className = "nav-accordion"
                  grpAccordion.onclick = function(e) {
                    e.preventDefault()
                    e.stopPropagation()
                    toggleSubmenu(grpAccordion)
                  }
                  const grpIcon = document.createElement("span")
                  grpIcon.className = `nav-accordion-icon ${grp.cards && grp.cards.length > 0 ? "open" : ""}`
                  grpIcon.textContent = grp.cards && grp.cards.length > 0 ? "+" : ""
                  grpAccordion.appendChild(grpIcon)
                  grpCont.appendChild(grpAccordion)

                  grpLi.appendChild(grpCont)

                  const cardsUl = document.createElement("ul")
                  cardsUl.className = "nav-list"
                  cardsUl.id = `group-${progKey}-${modKey}-${lesKey}-${grpKey}-submenu`
                  if (isActiveGrp) {
                    cardsUl.classList.add("expanded")
                    grpIcon.classList.replace("open", "close")
                    grpIcon.textContent = "✕"
                  }

                  if (grp.cards) {
                    grp.cards.forEach((card: any) => {
                      const cardLi = document.createElement("li")
                      cardLi.className = "nav-item"
                      const isActiveCard = isActiveGrp && currentParams.card_id === card.id
                      let colorClass = 'blue'
                      if (card.risk > 0.75) colorClass = 'red'
                      else if (card.risk > 0.5) colorClass = 'orange'
                      else if (card.risk > 0.25) colorClass = 'green'

                      const cardCont = document.createElement("div")
                      cardCont.className = `nav-link-container${isActiveCard ? " active" : ""}`
                      const cardLink = document.createElement("a")
                      cardLink.href = card.url
                      cardLink.className = "nav-link"
                      cardLink.target = "_parent"
                      cardLink.innerHTML = `
                        <span class="nav-circle ${colorClass}"></span>
                        <span class="nav-page-name${isActiveCard ? " active" : ""}">${card.name}</span>
                      `
                      cardCont.appendChild(cardLink)
                      cardLi.appendChild(cardCont)
                      cardsUl.appendChild(cardLi)
                    })
                    if (grp.has_more_cards) {
                      const moreLi = document.createElement("li")
                      moreLi.className = "nav-item"
                      const moreCont = document.createElement("div")
                      moreCont.className = "nav-link-container"
                      moreCont.innerHTML = `
                        <span class="nav-link">
                          <span class="nav-circle blue"></span>
                          <span class="nav-page-name" style="color: rgba(255, 255, 255, 0.5);">...ещё ${grp.more_cards_count} карточек</span>
                        </span>
                      `
                      moreLi.appendChild(moreCont)
                      cardsUl.appendChild(moreLi)
                    }
                  }

                  grpLi.appendChild(cardsUl)
                  groupsUl.appendChild(grpLi)
                })
              }

              lesLi.appendChild(groupsUl)
              lessonsUl.appendChild(lesLi)
            })
          }

          modLi.appendChild(lessonsUl)
          modulesUl.appendChild(modLi)
        })
      }

      programLi.appendChild(modulesUl)
      coursesNav.appendChild(programLi)
    })
  } else {
    const noCourses = document.createElement("div")
    noCourses.className = "loading"
    noCourses.textContent = "Нет данных о курсах"
    coursesNav.appendChild(noCourses)
  }

  // Привязываем target для ссылок
  document.querySelectorAll('.nav-link').forEach((el) => {
    (el as HTMLAnchorElement).target = '_parent'
  })
}

/**
 * Обработчик события render
 */
function onRender(event: Event): void {
  const data = (event as CustomEvent<RenderData>).detail
  // Извлекаем данные навигации, переданные из Python
  const navData = (data.args as any).navigationData
  generateNavigation(navData)
  Streamlit.setFrameHeight()
}

// Подписываемся на событие render и уведомляем, что компонент готов
Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender)
Streamlit.setComponentReady()
Streamlit.setFrameHeight()
