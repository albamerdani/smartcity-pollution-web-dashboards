import { createRouter,createWebHashHistory } from 'vue-router'
import Dashboard from '../views/live/Dashboard.vue'
import ForecastAdmin from '../views/live/ForecastAdmin.vue'
import { useAuthStore } from '../stores/auth'
const routes=[{path:'/',component:Dashboard},{path:'/monitorimi',component:Dashboard},{path:'/forecast',component:ForecastAdmin,meta:{staff:true}},{path:'/:pathMatch(.*)*',redirect:'/'}]
const router=createRouter({history:createWebHashHistory(),routes})
router.beforeEach(to=>{if(to.meta.staff&&!useAuthStore().isAuthenticated)return {path:'/',query:{login:'1'}}})
export default router
