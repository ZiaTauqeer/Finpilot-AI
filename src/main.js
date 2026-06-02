import { createApp } from 'vue'
import { registerSW } from 'virtual:pwa-register'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

app.use(router)

app.mount('#app')

registerSW({
	immediate: true,
})
