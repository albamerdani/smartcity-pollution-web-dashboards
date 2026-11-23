import {ref,computed} from 'vue'
const lang=ref(localStorage.getItem('smartcity_lang')==='en'?'en':'sq')
const dict={
 en:{title:'SmartCity Environmental Monitor',subtitle:'Public monitoring • Albania',map:'Environmental map',trends:'Historical trends',forecast:'ML forecasts',login:'Administrator login',logout:'Log out',city:'City',parameter:'Parameter',period:'Period',refresh:'Refresh',nodes:'Reporting nodes',empty:'No sensor data available for this selection.',source:'Source',updated:'Measured at',real:'Observed',predicted:'Predicted',legend:'Color bands',stale:'Old reading',mapNote:'Colored circles show a station zone, not an interpolated pollution surface.',account:'Staff account',password:'Password',signin:'Sign in',run:'Run prediction',horizon:'Horizon (hours)',status:'Status',all:'All cities',export:'Download CSV',lastMonth:'Last month',twoWeeks:'Last 2 weeks',lastWeek:'Last week',threeDays:'3 days ago',twoDays:'2 days ago',oneDay:'1 day ago',threeHours:'3 hours ago',now:'Now',pm25:'PM2.5',pm10:'PM10',temperature:'Temperature',humidity:'Humidity',pressure:'Pressure',uv:'UV index',noise:'Noise dB',back:'Dashboard',modelWarn:'Fallback baseline is not a trained ML forecast.',error:'Unable to retrieve data. Verify database and API connectivity.'},
 sq:{title:'Monitorimi Mjedisor SmartCity',subtitle:'Monitorim publik • Shqipëri',map:'Harta mjedisore',trends:'Tendencat historike',forecast:'Parashikime ML',login:'Hyrja e administratorit',logout:'Dil',city:'Qyteti',parameter:'Parametri',period:'Periudha',refresh:'Rifresko',nodes:'Nyje raportuese',empty:'Nuk ka matje për këtë përzgjedhje.',source:'Burimi',updated:'Koha e matjes',real:'Matje reale',predicted:'Parashikim',legend:'Nivelet e ngjyrave',stale:'Matje e vjetër',mapNote:'Rrathët me ngjyra tregojnë zonën e stacionit, jo një sipërfaqe ndotjeje të interpoluar.',account:'Llogaria e stafit',password:'Fjalëkalimi',signin:'Hyr',run:'Gjenero parashikimin',horizon:'Horizonti (orë)',status:'Statusi',all:'Të gjitha qytetet',export:'Shkarko CSV',lastMonth:'Muaji i fundit',twoWeeks:'2 javët e fundit',lastWeek:'Java e fundit',threeDays:'3 ditë më parë',twoDays:'2 ditë më parë',oneDay:'1 ditë më parë',threeHours:'3 orë më parë',now:'Tani',pm25:'PM2.5',pm10:'PM10',temperature:'Temperatura',humidity:'Lagështia',pressure:'Presioni',uv:'Indeksi UV',noise:'Zhurma dB',back:'Paneli publik',modelWarn:'Parashikimi bazë nuk është parashikim nga një model ML i trajnuar.',error:'Nuk mund të merren të dhënat. Kontrolloni lidhjen me bazën dhe API.'}
}
export function useLang(){const t=computed(()=>dict[lang.value]);const change=v=>{lang.value=v;localStorage.setItem('smartcity_lang',v)};return{lang,t,change}}
export const timeOptions=['month','2weeks','week','3days','2days','day','3hours','now']
export const labels=['lastMonth','twoWeeks','lastWeek','threeDays','twoDays','oneDay','threeHours','now']
export const cities=['Tirana','Elbasan','Korca']
export const params=['pm25','pm10','temperature','humidity','pressure','uv','noise']
// PM2.5/PM10 breakpoints are illustrative operational bands (µg/m³), not statutory AQI or WHO thresholds.
export function severity(value,param){if(value==null||!Number.isFinite(Number(value)))return '#9ca3af';const v=Number(value);let edges
 if(param==='temperature')edges=[10,25,32]
 else if(param==='pm25')edges=[10,25,50]
 else if(param==='pm10')edges=[20,50,100]
 else if(param==='humidity')edges=[30,60,80]
 else if(param==='noise')edges=[35,55,75]
 else if(param==='uv')edges=[3,6,8]
 else edges=[1000,1020,1040]
 return v<edges[0]?'#22a06b':v<edges[1]?'#eab308':v<edges[2]?'#f97316':'#dc2626'
}
