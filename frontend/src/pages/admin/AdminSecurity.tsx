import { useState } from 'react';
import { Alert, Box, Button, Paper, TextField, Typography } from '@mui/material';
import { confirmAdmin2FA, setupAdmin2FA } from '../../services/authService';
import { useAuthStore } from '../../stores/authStore';
export default function AdminSecurity(){
 const [setup,setSetup]=useState<{secret:string;otpauth_uri:string}|null>(null),[code,setCode]=useState(''),[message,setMessage]=useState(''),[error,setError]=useState(''); const logout=useAuthStore(s=>s.logout);
 async function start(){try{setSetup(await setupAdmin2FA());setError('')}catch{setError('Não foi possível iniciar o 2FA.')}}
 async function confirm(){try{const r=await confirmAdmin2FA(code);setMessage(r.message);logout()}catch{setError('Código inválido. Confira o relógio do dispositivo.')}}
 return <Box sx={{p:3,maxWidth:760}}><Typography variant="h4" sx={{fontWeight:800,mb:3}}>Segurança administrativa</Typography><Paper sx={{p:3}}><Typography variant="h6">Autenticação em dois fatores</Typography><Typography color="text.secondary" sx={{my:2}}>Proteja o painel usando um aplicativo autenticador compatível com TOTP.</Typography>{error&&<Alert severity="error" sx={{mb:2}}>{error}</Alert>}{message&&<Alert severity="success" sx={{mb:2}}>{message}</Alert>}{!setup?<Button variant="contained" onClick={start}>Configurar 2FA</Button>:<><Alert severity="warning" sx={{mb:2}}>Guarde a chave em local seguro. Ela será exibida somente durante esta configuração.</Alert><TextField fullWidth label="Chave manual" value={setup.secret} slotProps={{input:{readOnly:true}}} sx={{mb:2}}/><TextField fullWidth label="Endereço para aplicativo autenticador" value={setup.otpauth_uri} slotProps={{input:{readOnly:true}}} sx={{mb:2}}/><TextField label="Código de 6 dígitos" value={code} onChange={e=>setCode(e.target.value.replace(/\D/g,'').slice(0,6))}/><Button variant="contained" onClick={confirm} disabled={code.length!==6} sx={{ml:2}}>Ativar</Button></>}</Paper></Box>
}
