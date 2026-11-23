import client from './client'
export const getMap=(window,param,mode='observed')=>client.get('map/',{params:{window,param,mode}}).then(r=>r.data)
export const getTrends=(window,param,city)=>client.get('trends/',{params:{window,param,city}}).then(r=>r.data)
export const getOverview=()=>client.get('overview/').then(r=>r.data)
export const runForecast=(city,horizon_hours=24)=>client.post('forecasts/',{city:city||undefined,horizon_hours}).then(r=>r.data)
