<template>
<div class="app-page">
<header class="topnav"><div><strong>◉ SmartCity</strong><span class="muted">{{t.subtitle}}</span></div><div class="nav-actions"><select :value="lang" @change="change($event.target.value)"><option value="sq">Shqip</option><option value="en">English</option></select><router-link v-if="auth.isAuthenticated" to="/forecast" class="action">{{t.forecast}}</router-link><button v-else class="action" @click="showLogin=true">{{t.login}}</button><button v-if="auth.isAuthenticated" @click="auth.logout()">{{t.logout}}</button></div></header>
<main class="dashboard-shell"><div class="intro"><div><div class="eyebrow">ENVIRONMENTAL INTELLIGENCE</div><h1>{{t.title}}</h1><p>{{t.subtitle}} · PostgreSQL 16 / TimescaleDB · OpenStreetMap</p></div><button class="action" @click="reload">↻ {{t.refresh}}</button></div>
<section class="filters"><label>{{t.period}}<select v-model="period"><option v-for="(w,i) in timeOptions" :key="w" :value="w">{{t[labels[i]]}}</option></select></label><label>{{t.parameter}}<select v-model="param"><option v-for="p in params" :key="p" :value="p">{{t[p]}}</option></select></label><label>{{t.source}}<select v-model="mode"><option value="observed">{{t.real}}</option><option value="forecast">{{t.predicted}}</option></select></label><label>{{t.city}}<select v-model="city"><option value="">{{t.all}}</option><option v-for="c in cities" :key="c">{{c}}</option></select></label></section>
<div v-if="error" class="error-banner">{{t.error}} {{error}}</div>
<section class="metrics"><article class="metric"><span>{{t.nodes}}</span><strong>{{filtered.length}}</strong><small>{{mode==='observed'?t.real:t.predicted}}</small></article><article v-for="c in cities" :key="c" class="metric"><span>{{c}}</span><strong>{{format(average(c))}}</strong><small>{{t[param]}}</small></article></section>
<section class="two-cols"><article class="surface map-card"><div class="section-title"><h2>{{t.map}}</h2><span class="muted">{{t[labels[timeOptions.indexOf(period)]]}}</span></div><LeafletMap :points="filtered" :param="param"/><div class="legend"><span v-for="(color,i) in colors" :key="color"><b :style="{background:color}"></b>{{['Low / Ulët','Moderate / Mesatar','High / Lartë','Very high / Shumë i lartë'][i]}}</span></div><p class="note">{{t.mapNote}}</p></article><article class="surface"><div class="section-title"><h2>{{t.trends}}</h2><button class="link" @click="exportCsv">{{t.export}}</button></div><div class="trend-chart" v-if="chartSeries.length"><svg viewBox="0 0 620 270" preserveAspectRatio="none" role="img" aria-label="Historical hourly averaged trend"><line v-for="i in 5" :key="i" x1="34" :y1="15+(i-1)*55" x2="609" :y2="15+(i-1)*55" stroke="#e1e9e8"/><polyline v-for="c in visibleCities" :key="c" :points="spark(c)" fill="none" :stroke="cityColor[c]" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg></div><p v-else class="empty">{{t.empty}}</p><div class="city-legend"><span v-for="c in visibleCities" :key="c"><b :style="{background:cityColor[c]}"></b>{{c}}</span></div><p class="note">Hourly averages, observed database measurements.</p></article></section>
<section class="surface"><div class="section-title"><h2>{{t.nodes}}</h2><span class="muted">{{filtered.length}} stations</span></div><div class="tablewrap"><table><thead><tr><th>{{t.city}}</th><th>Node</th><th>{{t.parameter}}</th><th>{{t.updated}}</th><th>{{t.source}}</th></tr></thead><tbody><tr v-for="p in filtered" :key="p.node"><td>{{p.city}}</td><td>{{p.node}}</td><td><span class="color-dot" :style="{background:severity(p.value,param)}"></span>{{format(p.value)}}</td><td>{{new Date(p.timestamp).toLocaleString(lang==='sq'?'sq-AL':'en-GB')}}</td><td>{{p.source}} <small v-if="p.stale"> · {{t.stale}}</small></td></tr><tr v-if="!filtered.length"><td colspan="5">{{t.empty}}</td></tr></tbody></table></div></section>
</main>
<div v-if="showLogin" class="modal-back" @click.self="showLogin=false"><form class="login-panel" @submit.prevent="signin"><h2>{{t.login}}</h2><label>{{t.account}}<input v-model="username" required autocomplete="username"/></label><label>{{t.password}}<input v-model="password" type="password" required autocomplete="current-password"/></label><p v-if="loginError" class="error-banner">{{loginError}}</p><button class="action" :disabled="logging">{{t.signin}}</button><button type="button" @click="showLogin=false">✕</button></form></div>
</div>
</template>
<script setup>
import {ref,computed,onMounted,onUnmounted,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import LeafletMap from './LeafletMap.vue'
import {useLang,timeOptions,labels,cities,params,severity} from './i18n'
import {getMap,getTrends} from '../../api/dashboard'
import {useAuthStore} from '../../stores/auth'
const {lang,t,change}=useLang();const auth=useAuthStore();const route=useRoute();const router=useRouter()
const mode=ref('observed'),period=ref('now'),param=ref('pm25'),city=ref(''),points=ref([]),chartSeries=ref([]),error=ref('')
const showLogin=ref(!!route.query.login),username=ref(''),password=ref(''),loginError=ref(''),logging=ref(false)
const cityColor={Tirana:'#2563eb',Elbasan:'#16a34a',Korca:'#f97316'};const colors=['#22a06b','#eab308','#f97316','#dc2626']
const filtered=computed(()=>points.value.filter(p=>!city.value||p.city===city.value))
const visibleCities=computed(()=>city.value?[city.value]:cities)
function average(c){const nums=filtered.value.filter(p=>p.city===c).map(p=>Number(p.value)).filter(Number.isFinite);return nums.length?nums.reduce((a,b)=>a+b,0)/nums.length:null}
function format(v){return v==null||!Number.isFinite(Number(v))?'—':Number(v).toFixed(1)}
function spark(c){const vals=chartSeries.value.filter(x=>x.city===c),all=chartSeries.value.map(x=>x.value);if(!vals.length)return ''
 const ts=chartSeries.value.map(x=>Date.parse(x.timestamp)),mi=Math.min(...ts),ma=Math.max(...ts),lo=Math.min(...all),hi=Math.max(...all);return vals.map(v=>`${34+(Date.parse(v.timestamp)-mi)/(ma-mi||1)*575},${235-(v.value-lo)/(hi-lo||1)*210}`).join(' ')}
let request=0
async function reload(){const id=++request;error.value='';try{const [map,history]=await Promise.all([getMap(period.value,param.value,mode.value),getTrends(period.value,param.value,city.value||undefined)]);if(id!==request)return;points.value=map.points;chartSeries.value=history.series}catch(e){if(id===request){error.value=e.response?.status?String(e.response.status):'Network error';points.value=[];chartSeries.value=[]}}}
watch([period,param,city,mode],reload)
let timer
onMounted(()=>{reload();timer=setInterval(()=>{if(period.value==='now')reload()},30000)})
onUnmounted(()=>clearInterval(timer))
function exportCsv(){const rows=['timestamp,city,value,samples',...chartSeries.value.map(x=>[x.timestamp,x.city,x.value,x.samples].join(','))];const blob=new Blob([rows.join('\n')],{type:'text/csv'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='smartcity-trends.csv';a.click();URL.revokeObjectURL(url)}
async function signin(){logging.value=true;loginError.value='';try{await auth.login({username:username.value,password:password.value});showLogin.value=false;router.push('/forecast')}catch(e){loginError.value=e.response?.data?.detail||'Authentication failed'}finally{logging.value=false}}
</script>
