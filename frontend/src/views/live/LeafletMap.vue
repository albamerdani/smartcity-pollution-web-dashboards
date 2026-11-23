<template><div ref="mapRef" class="map-element" role="img" aria-label="OpenStreetMap monitoring stations"></div></template>
<script setup>
import {ref,onMounted,onBeforeUnmount,watch} from 'vue'
import L from 'leaflet'
import {severity} from './i18n'
const props=defineProps({points:{type:Array,default:()=>[]},param:{type:String,default:'pm25'},cities:{type:Array,default:()=>[]}})
const mapRef=ref(null);let map,layer
function draw(){if(!map)return;layer.clearLayers()
 for(const p of props.points){
  if(!Number.isFinite(Number(p.lat))||!Number.isFinite(Number(p.lon))||p.lat==null||p.lon==null)continue
  const color=severity(p.value,props.param)
  L.circle([Number(p.lat),Number(p.lon)],{radius:1400,color,weight:2,fillColor:color,fillOpacity:.22}).addTo(layer)
  const name=String(p.node||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')
  const title=String(p.location||p.city||'').replaceAll('&','&amp;').replaceAll('<','&lt;')
  L.circleMarker([Number(p.lat),Number(p.lon)],{radius:8,weight:2,color:'#fff',fillColor:color,fillOpacity:1}).bindPopup(`<strong>${name}</strong><p>${title}</p><strong>${p.value??'—'}</strong><p>${p.timestamp||''}</p>`).addTo(layer)
 }
}
onMounted(()=>{map=L.map(mapRef.value,{scrollWheelZoom:false}).setView([41.05,20.12],8)
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}).addTo(map)
 layer=L.layerGroup().addTo(map);draw();setTimeout(()=>map?.invalidateSize(),100)})
watch(()=>[props.points,props.param],draw,{deep:true})
onBeforeUnmount(()=>map?.remove())
</script>
