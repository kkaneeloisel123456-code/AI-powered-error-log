import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import { toastPlugin } from './components/common/toast'
import './styles/tokens.css'
import './styles/base.css'
import './styles/responsive.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(toastPlugin)
app.mount('#app')
