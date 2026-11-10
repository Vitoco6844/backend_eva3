(() => {
const canvas=document.querySelector('#signature-pad');if(!canvas)return;
const ctx=canvas.getContext('2d');let drawing=false,marked=false;
const reset=()=>{ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);marked=false;document.querySelector('[name=signature]').value='';};reset();
const point=e=>{const r=canvas.getBoundingClientRect();return [(e.clientX-r.left)*canvas.width/r.width,(e.clientY-r.top)*canvas.height/r.height];};
canvas.addEventListener('pointerdown',e=>{e.preventDefault();drawing=true;canvas.setPointerCapture(e.pointerId);ctx.beginPath();ctx.moveTo(...point(e));});
canvas.addEventListener('pointermove',e=>{if(!drawing)return;ctx.strokeStyle='#243e47';ctx.lineWidth=3;ctx.lineCap='round';ctx.lineTo(...point(e));ctx.stroke();marked=true;});
for(const event of ['pointerup','pointercancel'])canvas.addEventListener(event,()=>drawing=false);
document.querySelector('#clear-signature').addEventListener('click',reset);
document.querySelector('[data-signature-form]').addEventListener('submit',e=>{if(!marked){e.preventDefault();document.querySelector('#signature-error').textContent='Dibuja la firma del responsable antes de guardar.';canvas.focus();return;}document.querySelector('[name=signature]').value=canvas.toDataURL('image/png');});
})();