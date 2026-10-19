// SPDX-License-Identifier: GPL-3.0-only

(()=>{'use strict';
const $=s=>document.querySelector(s); const $$=s=>Array.from(document.querySelectorAll(s));
const languages={
 de:{cloudflareLabel:'Cloudflare Tunnel Token',cloudflareDeferred:'Ohne gültigen Tunnel-Token oder vorkonfigurierte Anmeldedatei ist das Profil noch nicht installierbar.',profileBuildDeferred:'Ausgewählte Dienste werden nicht stillschweigend ausgelassen. Fehlende Voraussetzungen vor der Installation beheben.',profileDeferred:'Wenn der Schlüssel noch fehlt, kann die Vorschau gespeichert werden, aber die Installation mit diesem ausgewählten Profil ist noch nicht bereit.',profileHeading:'Optionale Zusatzdienste',profileHint:'Optionales Profil sofort installieren (Häkchen) oder für später auslassen. Ausgewählte Dienste werden nie stillschweigend entfernt.',profileBuild:'Für lokal zu bauende Images muss das Original-Image vor der Installation vorhanden sein. Kein automatischer Ersatz.',profileAuth:'Tailscale-Authentifizierungsschlüssel',profileAuthNotice:'Der Schlüssel wird in der ZimaOS-Compose-Datei gespeichert.',profileChanged:'Profiländerung: Host-Ports erneut geprüft.',portReasonReserved:'Für ZimaOS/Monitor reservierter Port',portReasonDocker:'Docker-Container: {owner}',portReasonDuplicate:'Mehrfach in dieser Installation verwendet',portReasonHost:'NAS-Dienst oder anderer Prozess belegt den Port',portHeading:'Host-Ports prüfen',portRecheck:'Erneut prüfen',portExplanation:'Belegung auf dem NAS prüfen. Bei Konflikten kann der Host-Port direkt geändert werden.',portFree:'Frei',portOccupied:'Belegt',portPortChange:'Port auf {port} ändern',portNoFixed:'Keine festen Host-Ports vorhanden.',portChecking:'Host-Ports werden geprüft …',portChanged:'Host-Port aktualisiert. Compose vor Installation überprüfen.',portNotChecked:'Host-Portprüfung fehlgeschlagen. Installation nicht fortsetzen.',iconDetected:'Projekt-Logo wird nach Möglichkeit automatisch aus der Originalquelle übernommen.',projectLinkLabel:'Originalprojekt:',adminUsername:"Administrator-Benutzername",loginTitle:'Anmeldung',loginHint:"Mit dem festgelegten Benutzernamen und Passwort anmelden.",password:'Passwort',login:'Anmelden',ready:'BEREIT',running:'LAUFEND',stopped:'GESTOPPT',total:'DOCKER',services:'DIENSTE',newInstall:'NEUE INSTALLATION',readyStatus:'Install Monitor ist bereit',searchPlaceholder:'Docker durchsuchen …',installTab:'Installieren',appsTab:'Docker Apps',refresh:'Aktualisieren',source:'Quelle',configuration:'Konfiguration',review:'Prüfen',installation:'Installation',sourceTitle:'Docker-Quelle auswählen',sourceSubtitle:'Docker Hub, GHCR, GitHub, App-Kataloge oder Compose YAML',imageInput:'Docker-Image',imageHint:'Docker Hub, GHCR oder Registry-Image. Ports und Ordner unten festlegen.',urlInput:'HTTPS-Projektlink oder Compose-Datei',urlHint:'GitHub-, GitLab- oder Codeberg-Projekt, Release-Seite oder direkter Compose-Dateilink.',resolvedCompose:'Gefundene Compose-Datei',yamlInput:'Docker Compose YAML',yamlHint:'Komplette docker-compose.yml hier einfügen.',containerPort:'Container-Port (optional)',hostPort:'Host-Port (optional)',configPath:'Datenpfad im Container (optional)',analyze:'Quelle analysieren →',configHint:'Anzeigenamen, Speicherorte und App-Metadaten anpassen',appName:'App-Name',displayName:'Anzeigename',dataDir:'Basisordner für App-Daten',iconUrl:'Icon-URL (optional)',category:'Kategorie',composeSource:'Quell-Compose (bearbeitbar)',back:'Zurück',preview:'Vorschau erstellen →',reviewTitle:'ZimaOS-Konfiguration prüfen',reviewSubtitle:'Compose ansehen und vor der Installation bei Bedarf bearbeiten',generatedCompose:'Docker-Compose-Konfiguration',download:'YAML herunterladen',continue:'Weiter zur Installation →',installTitle:'Auf dem NAS installieren',credentialsHint:'ZimaOS-Anmeldedaten werden nur für diese Anfrage verwendet und nicht gespeichert.',zimaHost:'ZimaOS-Adresse',zimaUser:'ZimaOS-Benutzer',confirmText:'Ich habe die Compose-Konfiguration überprüft und bestätige die Installation auf meinem NAS.',installNow:'Jetzt auf dem NAS installieren',verify:'Container prüfen',settings:'Einstellungen',language:'Sprache',display:'Darstellung',darkOnly:'Dunkelmodus',logout:'Abmelden',invalid:'Bitte gültige Werte eingeben.',analyzing:'Quelle wird geprüft …',previewing:'Compose wird erstellt …',installing:'Installationsauftrag wird gesendet …',verifying:'ZimaOS-Container werden überprüft …',accepted:'Auftrag angenommen. Die App muss noch tatsächlich starten.',verifyDone:'ZimaOS hat Containerinformationen zurückgegeben. Den Status unten prüfen.',noDocker:'Docker-Socket nicht verfügbar.',empty:'Keine Docker-Container gefunden.',connection:'Docker-Status',noSearch:'Keine passenden Docker-Container.',loading:'Docker-Container werden geladen …',downloadName:'ZimaOS Compose herunterladen',warning:'Hinweise',success:'ZimaOS hat den Auftrag angenommen. Bitte den Containerstatus prüfen.',needConfirm:'Bestätige zuerst die Compose-Prüfung.',existing:'Vorhandene Apps werden nicht überschrieben.'},
 en:{cloudflareLabel:'Cloudflare tunnel token',cloudflareDeferred:'Without a tunnel token or preconfigured credentials this selected profile is not ready to install.',profileBuildDeferred:"Selected services are never silently skipped. Resolve missing requirements before installation.",profileDeferred:'You can preview without a key, but a selected profile cannot be installed until its requirements are met.',profileHeading:'Optional services',profileHint:'Check a profile to install it now, or leave unchecked for later. Selected services are never silently omitted.',profileBuild:'Locally built images must be provided before installation. No silent substitution.',profileAuth:'Tailscale authentication key',profileAuthNotice:'The key is stored in the ZimaOS Compose file.',profileChanged:'Profiles changed: host ports checked again.',portReasonReserved:'Reserved by ZimaOS/Monitor',portReasonDocker:'Docker container: {owner}',portReasonDuplicate:'Used more than once in this installation',portReasonHost:'NAS service or another process is using this port',portHeading:'Check host ports',portRecheck:'Check again',portExplanation:'Check NAS port availability. If occupied, you can change the host port here.',portFree:'Available',portOccupied:'Occupied',portPortChange:'Change port to {port}',portNoFixed:'No fixed host ports found.',portChecking:'Checking host ports …',portChanged:'Host port updated. Review Compose before installation.',portNotChecked:'Host port check failed. Do not proceed with installation.',iconDetected:'Project icon will be loaded from the original source when available.',projectLinkLabel:'Upstream project:',adminUsername:"Administrator username",loginTitle:'Sign in',loginHint:"Sign in using your configured username and password.",password:'Password',login:'Sign in',ready:'READY',running:'RUNNING',stopped:'STOPPED',total:'DOCKER',services:'SERVICES',newInstall:'NEW INSTALLATION',readyStatus:'Install Monitor is ready',searchPlaceholder:'Search containers …',installTab:'Install',appsTab:'Docker apps',refresh:'Refresh',source:'Source',configuration:'Configuration',review:'Review',installation:'Installation',sourceTitle:'Choose Docker source',sourceSubtitle:'Docker Hub, GHCR, GitHub, app catalogs or Compose YAML',imageInput:'Docker image',imageHint:'Docker Hub, GHCR or registry image. Define ports and folders below.',urlInput:'HTTPS project or Compose URL',urlHint:'GitHub, GitLab or Codeberg repository, release page or direct Compose file URL.',resolvedCompose:'Detected Compose file',yamlInput:'Docker Compose YAML',yamlHint:'Paste complete docker-compose.yml here.',containerPort:'Container port (optional)',hostPort:'Host port (optional)',configPath:'Container data path (optional)',analyze:'Analyze source →',configHint:'Customize name, data folders and app metadata',appName:'App name',displayName:'Display name',dataDir:'Base app-data folder',iconUrl:'Icon URL (optional)',category:'Category',composeSource:'Source Compose (editable)',back:'Back',preview:'Create preview →',reviewTitle:'Review ZimaOS configuration',reviewSubtitle:'Read and edit Compose before installation',generatedCompose:'Docker Compose configuration',download:'Download YAML',continue:'Continue to installation →',installTitle:'Install directly onto ZimaOS',credentialsHint:'ZimaOS credentials are used only for this request and are not stored.',zimaHost:'ZimaOS address',zimaUser:'ZimaOS user',confirmText:'I have reviewed this Compose configuration and confirm installation on my NAS.',installNow:'Install on NAS now',verify:'Check containers',settings:'Settings',language:'Language',display:'Appearance',darkOnly:'Dark mode',logout:'Sign out',invalid:'Enter valid values.',analyzing:'Analyzing source …',previewing:'Generating Compose …',installing:'Sending installation request …',verifying:'Checking ZimaOS containers …',accepted:'Request accepted. The app still needs to start successfully.',verifyDone:'ZimaOS returned container information. Check the status below.',noDocker:'Docker socket is unavailable.',empty:'No Docker containers found.',connection:'Docker state',noSearch:'No matching Docker containers.',loading:'Loading Docker containers …',warning:'Notes',success:'ZimaOS accepted the request. Verify the containers.',needConfirm:'Please confirm your review of the Compose file.',existing:'Existing apps are not overwritten.',downloadName:'Download ZimaOS Compose'},
 fr:{cloudflareLabel:'Jeton Cloudflare Tunnel',cloudflareDeferred:'Sans jeton ou identifiants préconfigurés, ce profil ne peut pas encore être installé.',profileBuildDeferred:"Les services sélectionnés ne sont jamais ignorés. Résolvez les prérequis manquants avant l’installation.",profileDeferred:'La prévisualisation reste possible, mais les identifiants manquants bloquent l’installation du profil sélectionné.',profileHeading:'Services optionnels',profileHint:'Cocher pour installer maintenant, sinon laisser pour plus tard. Les services sélectionnés ne sont jamais ignorés.',profileBuild:'Les images locales doivent exister avant l’installation. Aucun remplacement automatique.',profileAuth:'Clé d’authentification Tailscale',profileAuthNotice:'Cette clé est enregistrée dans le fichier Compose ZimaOS.',profileChanged:'Profils modifiés : ports revérifiés.',portReasonReserved:'Réservé par ZimaOS/Monitor',portReasonDocker:'Conteneur Docker : {owner}',portReasonDuplicate:'Utilisé plusieurs fois dans cette installation',portReasonHost:'Service NAS ou autre processus utilise ce port',portHeading:'Vérifier les ports hôte',portRecheck:'Revérifier',portExplanation:'Vérifiez les ports du NAS et changez-les si nécessaire.',portFree:'Libre',portOccupied:'Occupé',portPortChange:'Changer le port vers {port}',portNoFixed:'Aucun port hôte fixe.',portChecking:'Vérification des ports …',portChanged:'Port modifié. Vérifiez le Compose avant installation.',portNotChecked:'Vérification impossible. Ne lancez pas l’installation.',iconDetected:'L’icône provient du projet d’origine, si disponible.',projectLinkLabel:'Projet d’origine :',adminUsername:"Nom d’utilisateur administrateur",loginTitle:'Connexion',loginHint:"Connectez-vous avec votre identifiant et votre mot de passe.",password:'Mot de passe',login:'Connexion',ready:'PRÊT',running:'ACTIF',stopped:'ARRÊTÉ',total:'DOCKER',services:'SERVICES',newInstall:'NOUVELLE INSTALLATION',readyStatus:'Install Monitor est prêt',searchPlaceholder:'Rechercher les conteneurs …',installTab:'Installer',appsTab:'Applications Docker',refresh:'Actualiser',source:'Source',configuration:'Configuration',review:'Vérifier',installation:'Installation',sourceTitle:'Choisir la source Docker',sourceSubtitle:'Docker Hub, GHCR, GitHub, catalogues d’apps ou Compose YAML',imageInput:'Image Docker',imageHint:'Précisez les ports et dossiers ci-dessous.',urlInput:'URL HTTPS du projet ou Compose',urlHint:'Dépôt GitHub, GitLab ou Codeberg, page de version ou fichier Compose direct.',resolvedCompose:'Fichier Compose trouvé',yamlInput:'Docker Compose YAML',yamlHint:'Coller la configuration complète.',containerPort:'Port du conteneur (facultatif)',hostPort:'Port hôte (facultatif)',configPath:'Dossier du conteneur (facultatif)',analyze:'Analyser la source →',configHint:'Personnaliser les chemins et les métadonnées',appName:'Nom de l’application',displayName:'Nom affiché',dataDir:'Dossier de données',iconUrl:'URL de l’icône (facultatif)',category:'Catégorie',composeSource:'Compose source (modifiable)',back:'Retour',preview:'Prévisualiser →',reviewTitle:'Vérifier la configuration ZimaOS',reviewSubtitle:'Vérifiez et modifiez Compose avant installation',generatedCompose:'Configuration Docker Compose',download:'Télécharger YAML',continue:'Continuer →',installTitle:'Installer sur le NAS',credentialsHint:'Les identifiants ne sont ni conservés ni enregistrés.',zimaHost:'Adresse ZimaOS',zimaUser:'Utilisateur ZimaOS',confirmText:'J’ai vérifié cette configuration et confirme son installation.',installNow:'Installer sur le NAS',verify:'Vérifier les conteneurs',settings:'Paramètres',language:'Langue',display:'Apparence',darkOnly:'Mode sombre',logout:'Déconnexion',invalid:'Saisissez des valeurs valides.',analyzing:'Analyse en cours …',previewing:'Préparation du Compose …',installing:'Envoi de l’installation …',verifying:'Vérification des conteneurs …',accepted:'Demande acceptée; le démarrage reste à vérifier.',verifyDone:'Informations de conteneurs reçues.',noDocker:'Socket Docker inaccessible.',empty:'Aucun conteneur trouvé.',connection:'Statut Docker',noSearch:'Aucun conteneur correspondant.',loading:'Chargement des conteneurs …',warning:'Remarques',success:'Demande acceptée. Vérifiez les conteneurs.',needConfirm:'Confirmez la vérification du Compose.',existing:'Les apps existantes ne sont pas écrasées.',downloadName:'Télécharger le Compose ZimaOS'},
 pt:{cloudflareLabel:'Token do Cloudflare Tunnel',cloudflareDeferred:'Sem token ou credenciais já configuradas, este perfil ainda não pode ser instalado.',profileBuildDeferred:"Os serviços selecionados nunca são ignorados sem aviso. Resolva os requisitos em falta antes da instalação.",profileDeferred:'Pode pré-visualizar sem chave, mas a instalação do perfil selecionado exige as credenciais necessárias.',profileHeading:'Serviços opcionais',profileHint:'Selecione para instalar agora ou deixe desmarcado para mais tarde. Serviços selecionados não são omitidos.',profileBuild:'As imagens locais têm de existir antes da instalação. Sem substituição automática.',profileAuth:'Chave de autenticação Tailscale',profileAuthNotice:'A chave será guardada no ficheiro Compose do ZimaOS.',profileChanged:'Perfis alterados: portas verificadas novamente.',portReasonReserved:'Reservada para ZimaOS/Monitor',portReasonDocker:'Contentor Docker: {owner}',portReasonDuplicate:'Usada várias vezes nesta instalação',portReasonHost:'Serviço NAS ou outro processo ocupa a porta',portHeading:'Verificar portas do NAS',portRecheck:'Verificar novamente',portExplanation:'Verificar portas do NAS e alterar as ocupadas.',portFree:'Livre',portOccupied:'Ocupada',portPortChange:'Mudar para a porta {port}',portNoFixed:'Sem portas fixas.',portChecking:'A verificar portas …',portChanged:'Porta alterada. Confirme o Compose antes de instalar.',portNotChecked:'Não foi possível verificar. Não prossiga com a instalação.',iconDetected:'O ícone é obtido do projeto original quando disponível.',projectLinkLabel:'Projeto original:',adminUsername:"Nome de utilizador administrador",loginTitle:'Iniciar sessão',loginHint:"Entre com o nome de utilizador e a palavra-passe definidos.",password:'Palavra-passe',login:'Entrar',ready:'PRONTO',running:'ATIVO',stopped:'PARADO',total:'DOCKER',services:'SERVIÇOS',newInstall:'NOVA INSTALAÇÃO',readyStatus:'Install Monitor está pronto',searchPlaceholder:'Pesquisar contentores …',installTab:'Instalar',appsTab:'Apps Docker',refresh:'Atualizar',source:'Origem',configuration:'Configuração',review:'Verificar',installation:'Instalação',sourceTitle:'Selecionar origem Docker',sourceSubtitle:'Docker Hub, GHCR, GitHub, catálogos de apps ou Compose YAML',imageInput:'Imagem Docker',imageHint:'Defina as portas e as pastas abaixo.',urlInput:'URL HTTPS do projeto ou Compose',urlHint:'Repositório GitHub, GitLab ou Codeberg, página de versões ou ficheiro Compose direto.',resolvedCompose:'Ficheiro Compose encontrado',yamlInput:'Docker Compose YAML',yamlHint:'Cole aqui a configuração completa.',containerPort:'Porta do contentor (opcional)',hostPort:'Porta do NAS (opcional)',configPath:'Pasta no contentor (opcional)',analyze:'Analisar origem →',configHint:'Alterar nomes, pastas e metadados',appName:'Nome da app',displayName:'Nome visível',dataDir:'Pasta de dados',iconUrl:'URL do ícone (opcional)',category:'Categoria',composeSource:'Compose original (editável)',back:'Voltar',preview:'Criar pré-visualização →',reviewTitle:'Verificar configuração ZimaOS',reviewSubtitle:'Veja e edite o Compose antes de instalar',generatedCompose:'Configuração Docker Compose',download:'Descarregar YAML',continue:'Continuar →',installTitle:'Instalar no NAS',credentialsHint:'As credenciais são usadas apenas neste pedido e não são guardadas.',zimaHost:'Endereço ZimaOS',zimaUser:'Utilizador ZimaOS',confirmText:'Verifiquei esta configuração e confirmo a instalação no NAS.',installNow:'Instalar no NAS',verify:'Verificar contentores',settings:'Definições',language:'Idioma',display:'Aspeto',darkOnly:'Modo escuro',logout:'Terminar sessão',invalid:'Introduza valores válidos.',analyzing:'A analisar origem …',previewing:'A gerar Compose …',installing:'A enviar instalação …',verifying:'A verificar os contentores …',accepted:'Pedido aceite; falta confirmar o arranque.',verifyDone:'Dados dos contentores recebidos.',noDocker:'Socket Docker indisponível.',empty:'Nenhum contentor encontrado.',connection:'Estado Docker',noSearch:'Nenhum contentor correspondente.',loading:'A carregar contentores …',warning:'Avisos',success:'Pedido aceite. Verifique os contentores.',needConfirm:'Confirme a revisão do Compose.',existing:'Apps existentes não são substituídas.',downloadName:'Transferir Compose ZimaOS'},
 es:{cloudflareLabel:'Token de Cloudflare Tunnel',cloudflareDeferred:'Sin token o credenciales preconfiguradas, este perfil no está listo para instalar.',profileBuildDeferred:"Los servicios seleccionados nunca se omiten sin avisar. Resuelve los requisitos pendientes antes de instalar.",profileDeferred:'La vista previa funciona sin clave, pero la instalación del perfil seleccionado requiere las credenciales.',profileHeading:'Servicios opcionales',profileHint:'Marcar para instalar ahora, dejar sin marcar para después. Nunca se omiten servicios seleccionados.',profileBuild:'Las imágenes locales deben existir antes de la instalación. Sin sustitución automática.',profileAuth:'Clave de autenticación Tailscale',profileAuthNotice:'La clave se almacena en el archivo Compose de ZimaOS.',profileChanged:'Perfiles modificados: puertos comprobados otra vez.',portReasonReserved:'Reservado por ZimaOS/Monitor',portReasonDocker:'Contenedor Docker: {owner}',portReasonDuplicate:'Repetido en esta instalación',portReasonHost:'Un servicio NAS u otro proceso utiliza el puerto',portHeading:'Comprobar puertos del NAS',portRecheck:'Volver a comprobar',portExplanation:'Comprobar puertos del NAS y cambiar los ocupados.',portFree:'Libre',portOccupied:'Ocupado',portPortChange:'Cambiar al puerto {port}',portNoFixed:'No hay puertos fijos.',portChecking:'Comprobando puertos …',portChanged:'Puerto actualizado. Revisa Compose antes de instalar.',portNotChecked:'No se pudo comprobar. No continúes la instalación.',iconDetected:'El icono procede del proyecto original, si está disponible.',projectLinkLabel:'Proyecto original:',adminUsername:"Nombre de usuario administrador",loginTitle:'Iniciar sesión',loginHint:"Inicia sesión con el usuario y la contraseña configurados.",password:'Contraseña',login:'Entrar',ready:'LISTO',running:'ACTIVO',stopped:'DETENIDO',total:'DOCKER',services:'SERVICIOS',newInstall:'NUEVA INSTALACIÓN',readyStatus:'Install Monitor está listo',searchPlaceholder:'Buscar contenedores …',installTab:'Instalar',appsTab:'Apps Docker',refresh:'Actualizar',source:'Origen',configuration:'Configuración',review:'Revisar',installation:'Instalación',sourceTitle:'Seleccionar origen Docker',sourceSubtitle:'Docker Hub, GHCR, GitHub, catálogos de apps o Compose YAML',imageInput:'Imagen Docker',imageHint:'Configura los puertos y las carpetas abajo.',urlInput:'URL HTTPS del proyecto o Compose',urlHint:'Repositorio GitHub, GitLab o Codeberg, página de versiones o archivo Compose directo.',resolvedCompose:'Archivo Compose encontrado',yamlInput:'Docker Compose YAML',yamlHint:'Pega aquí toda la configuración.',containerPort:'Puerto del contenedor (opcional)',hostPort:'Puerto del NAS (opcional)',configPath:'Carpeta del contenedor (opcional)',analyze:'Analizar origen →',configHint:'Editar nombres, carpetas y metadatos',appName:'Nombre de app',displayName:'Nombre visible',dataDir:'Carpeta de datos',iconUrl:'URL del icono (opcional)',category:'Categoría',composeSource:'Compose original (editable)',back:'Volver',preview:'Crear vista previa →',reviewTitle:'Revisar configuración ZimaOS',reviewSubtitle:'Revisa y edita Compose antes de instalar',generatedCompose:'Configuración Docker Compose',download:'Descargar YAML',continue:'Continuar →',installTitle:'Instalar en el NAS',credentialsHint:'Las credenciales se usan solo para esta solicitud y no se guardan.',zimaHost:'Dirección ZimaOS',zimaUser:'Usuario ZimaOS',confirmText:'He revisado esta configuración y confirmo la instalación en mi NAS.',installNow:'Instalar en el NAS',verify:'Comprobar contenedores',settings:'Configuración',language:'Idioma',display:'Apariencia',darkOnly:'Modo oscuro',logout:'Cerrar sesión',invalid:'Introduce valores válidos.',analyzing:'Analizando origen …',previewing:'Preparando Compose …',installing:'Enviando instalación …',verifying:'Comprobando contenedores …',accepted:'Solicitud aceptada; falta verificar el inicio.',verifyDone:'Datos de contenedores recibidos.',noDocker:'Socket Docker no disponible.',empty:'No se encontraron contenedores.',connection:'Estado Docker',noSearch:'Sin contenedores coincidentes.',loading:'Cargando contenedores …',warning:'Avisos',success:'Solicitud aceptada. Verifica los contenedores.',needConfirm:'Confirma la revisión de Compose.',existing:'Las apps existentes no se sobrescriben.',downloadName:'Descargar Compose ZimaOS'},
};

let lsioImages=null, lsioSelected='', lsioLoading=null;
const lsioWords={
 de:{hint:'Offizieller LinuxServer.io-Katalog. Image auswählen; Pflicht-Ports und Pflicht-Volumes werden übernommen.',search:'Images durchsuchen…',all:'Alle Kategorien',load:'Katalog wird geladen…',unavailable:'Katalog konnte nicht geladen werden:',empty:'Keine passenden Images gefunden.',select:'Ausgewählt',count:'Images',catalog:'Offizielle Image-Daten; weitere Einrichtung laut Anbieter-Dokumentation prüfen.'},
 en:{hint:'Official LinuxServer.io catalog. Select an image to load documented required ports and volumes.',search:'Search images…',all:'All categories',load:'Loading catalog…',unavailable:'Catalog unavailable:',empty:'No matching images.',select:'Selected',count:'images',catalog:'Official image data; review additional setup in publisher documentation.'},
 fr:{hint:'Catalogue officiel LinuxServer.io. Les ports et volumes obligatoires sont repris.',search:'Rechercher des images…',all:'Toutes les catégories',load:'Chargement du catalogue…',unavailable:'Catalogue indisponible :',empty:'Aucune image correspondante.',select:'Sélectionné',count:'images',catalog:'Données officielles ; vérifier la documentation du fournisseur.'},
 pt:{hint:'Catálogo oficial LinuxServer.io. As portas e os volumes obrigatórios são preenchidos.',search:'Pesquisar imagens…',all:'Todas as categorias',load:'A carregar catálogo…',unavailable:'Catálogo indisponível:',empty:'Nenhuma imagem encontrada.',select:'Selecionado',count:'imagens',catalog:'Dados oficiais; verificar a documentação de instalação.'},
 es:{hint:'Catálogo oficial LinuxServer.io. Se cargan los puertos y volúmenes obligatorios.',search:'Buscar imágenes…',all:'Todas las categorías',load:'Cargando catálogo…',unavailable:'Catálogo no disponible:',empty:'No se encontraron imágenes.',select:'Seleccionado',count:'imágenes',catalog:'Datos oficiales; revisar la documentación de instalación.'}
};
const lw=k=>lsioWords[lang]?.[k]||lsioWords.de[k]||k;
async function loadLsio(){
 if(lsioImages){renderLsio();return;}
 if(lsioLoading)return lsioLoading;
 $('#lsioStatus').textContent=lw('load');
 lsioLoading=(async()=>{
  try{
   const response=await request('/api/linuxserver/images');
   lsioImages=Array.isArray(response.images)?response.images:[];
   const select=$('#lsioCategory');const current=select.value;
   const categories=[...new Set(lsioImages.map(v=>v.category).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
   select.replaceChildren();
   const all=document.createElement('option');all.value='';all.textContent=lw('all');select.appendChild(all);
   for(const category of categories){const option=document.createElement('option');option.value=category;option.textContent=category;select.appendChild(option)}
   select.value=current;
   renderLsio();
  }catch(e){$('#lsioStatus').textContent=lw('unavailable')+' '+errorMessage(e);}
  finally{lsioLoading=null;}
 })();
 return lsioLoading;
}
function renderLsio(){
 const list=$('#lsioList');list.replaceChildren();
 if(!lsioImages){return}
 const q=$('#lsioSearch').value.toLocaleLowerCase().trim();const category=$('#lsioCategory').value;
 const results=lsioImages.filter(v=>(!category||v.category===category)&&(!q||[v.name,v.description,v.category].join(' ').toLocaleLowerCase().includes(q)));
 $('#lsioStatus').textContent=results.length+' '+lw('count')+' · '+lw('catalog');
 for(const entry of results.slice(0,250)){
  const button=document.createElement('button');button.type='button';button.className='im-lsio-entry';
  button.setAttribute('role','listitem');button.setAttribute('aria-pressed',String(lsioSelected===entry.name));
  const logoWrap=document.createElement('span');logoWrap.className='im-lsio-entry-logo';
   const logo=document.createElement('img');logo.alt='';logo.loading='lazy';logo.decoding='async';logo.referrerPolicy='no-referrer';
   const fallback=document.createElement('span');fallback.className='im-lsio-logo-fallback';fallback.textContent=entry.name.slice(0,2).toUpperCase();
   const fallbackUrl='https://cdn.jsdelivr.net/gh/selfhst/icons/png/'+entry.name.replace(/[^a-z0-9-]/g,'-')+'.png';
   let triedFallback=false;
   logo.onerror=()=>{if(!triedFallback&&entry.project_logo){triedFallback=true;logo.src=fallbackUrl;return;}logoWrap.classList.add('im-lsio-logo-missing');};
   logo.src=entry.project_logo&&entry.project_logo.startsWith('https://')?entry.project_logo:fallbackUrl;
   logoWrap.append(logo,fallback);
   const body=document.createElement('span');body.className='im-lsio-entry-body';
  const title=document.createElement('strong');title.textContent=entry.name;
  const subtitle=document.createElement('small');subtitle.textContent=[entry.category,entry.description].filter(Boolean).join(' · ').slice(0,340);
  const meta=document.createElement('span');meta.className='im-lsio-entry-version';meta.textContent=entry.version||'';
  body.append(title,subtitle);button.append(logoWrap,body,meta);
  button.onclick=()=>{if(busy)return;lsioSelected=entry.name;$('#imStoresLsioAnalyze').disabled=false;$('#sourceInput').value=entry.name;$('#lsioSelection').hidden=false;$('#lsioSelection').textContent=lw('select')+': lscr.io/linuxserver/'+entry.name+':latest';renderLsio()};
  list.appendChild(button);
 }
 if(!results.length)list.textContent=lw('empty');
}

// v0.2.21: show the COMPLETE selfh.st index, with on-demand public GitHub
// repository search. Found does not mean installable; selecting a source
// triggers the EXISTING safe Compose analysis, never an automatic install.
let selfhstApps=null, selfhstAppsLoading=null, selfhstAppsCatalogError='';
let selfhstAppsSortMode='new'; // Only the five visible tabs control the catalog order.
let selfhstAppsRemoteQuery='',selfhstAppsRemoteRows=[],selfhstAppsRemotePage=0;
let selfhstAppsRemoteTotal=0,selfhstAppsRemoteMore=false,selfhstAppsRemoteBusy=false;
let selfhstAppsRemoteError='',selfhstAppsSearchSeq=0,selfhstAppsSearchTimer=null;
const selfhstAppLabels={
 de:{tab:'App-Katalog',search:'Apps durchsuchen – auch weltweit auf GitHub…',updated:'Zuletzt aktiv',popular:'Beliebteste',name:'Name A–Z',loading:'selfh.st-Katalog wird geladen…',error:'Katalog nicht verfügbar: ',none:'Keine Treffer. GitHub-Suche prüfen oder direkten Projektlink verwenden.',source:'selfh.st + öffentliche GitHub-Suche; Installation erst nach Analyse.',website:'Website ↗',repo:'Repository ↗',use:'Analysieren',count:'Apps',all:'Alle Kategorien',stale:'Zwischengespeicherter Katalog.',idle:'Ab zwei Zeichen wird zusätzlich auf GitHub gesucht. Alle selfh.st-Apps sind eingeblendet.',searching:'Suche auf GitHub…',matches:'GitHub-Treffer',limited:'GitHub liefert höchstens 1.000 Treffer je Suche. Begriff präzisieren.',moreGithub:'Weitere GitHub-Treffer',githubFail:'GitHub-Suche nicht verfügbar:',githubGroup:'GitHub – zusätzliche Projekte',selfhstGroup:'selfh.st – vollständiger Katalog',archived:'Archiviert',fork:'Fork',noRepo:'Kein Repository hinterlegt',tabPopular:'Beliebt',tabTrending:'Im Trend',tabNew:'Neu',trendExplanation:'Trend = Schätzung aus Sternen und letzter Aktivität; keine offizielle selfh.st-Trendrangliste.'},
 en:{tab:'App directory',search:'Search apps – including public GitHub repositories…',updated:'Recently active',popular:'Most popular',name:'Name A–Z',loading:'Loading selfh.st directory…',error:'Directory unavailable: ',none:'No matches. Try GitHub search or paste a repository URL.',source:'selfh.st + public GitHub search; analyze before installing.',website:'Website ↗',repo:'Repository ↗',use:'Analyze',count:'apps',all:'All categories',stale:'Cached directory.',idle:'Enter two or more characters to search GitHub as well. All selfh.st apps are listed.',searching:'Searching GitHub…',matches:'GitHub results',limited:'GitHub returns at most 1,000 matches per search. Refine your search.',moreGithub:'More GitHub results',githubFail:'GitHub search unavailable:',githubGroup:'GitHub – additional projects',selfhstGroup:'selfh.st – complete directory',archived:'Archived',fork:'Fork',noRepo:'No repository listed',tabPopular:'Popular',tabTrending:'Trending',tabNew:'New',trendExplanation:'Trending is an estimate from stars and recent activity, not the official selfh.st ranking.'},
 fr:{tab:'Catalogue d’apps',search:'Rechercher aussi dans les projets GitHub publics…',updated:'Activité récente',popular:'Popularité',name:'Nom A–Z',loading:'Chargement du catalogue selfh.st…',error:'Catalogue indisponible : ',none:'Aucun résultat. Recherchez sur GitHub ou collez un lien.',source:'selfh.st et recherche GitHub ; analyser avant installation.',website:'Site ↗',repo:'Dépôt ↗',use:'Analyser',count:'apps',all:'Toutes catégories',stale:'Catalogue en cache.',idle:'Deux caractères minimum pour rechercher aussi sur GitHub. Toutes les apps selfh.st sont affichées.',searching:'Recherche GitHub…',matches:'Résultats GitHub',limited:'GitHub limite les résultats à 1 000. Précisez la recherche.',moreGithub:'Autres résultats GitHub',githubFail:'Recherche GitHub indisponible :',githubGroup:'GitHub – autres projets',selfhstGroup:'selfh.st – catalogue complet',archived:'Archivé',fork:'Fork',noRepo:'Aucun dépôt',tabPopular:'Populaires',tabTrending:'Tendances',tabNew:'Nouveautés',trendExplanation:'Tendance estimée selon les étoiles et l’activité, pas le classement officiel de selfh.st.'},
 pt:{tab:'Catálogo de apps',search:'Pesquisar também nos projetos públicos do GitHub…',updated:'Atividade recente',popular:'Populares',name:'Nome A–Z',loading:'A carregar catálogo selfh.st…',error:'Catálogo indisponível: ',none:'Sem resultados. Pesquise no GitHub ou cole o endereço.',source:'selfh.st e pesquisa GitHub; analisar antes de instalar.',website:'Site ↗',repo:'Repositório ↗',use:'Analisar',count:'apps',all:'Todas as categorias',stale:'Catálogo em cache.',idle:'Introduza dois caracteres para pesquisar também no GitHub. Todas as apps selfh.st aparecem.',searching:'A pesquisar no GitHub…',matches:'Resultados GitHub',limited:'O GitHub limita a 1 000 resultados. Refine a pesquisa.',moreGithub:'Mais resultados GitHub',githubFail:'Pesquisa GitHub indisponível:',githubGroup:'GitHub – projetos adicionais',selfhstGroup:'selfh.st – catálogo completo',archived:'Arquivado',fork:'Fork',noRepo:'Sem repositório',tabPopular:'Populares',tabTrending:'Tendências',tabNew:'Novidades',trendExplanation:'Tendências estimadas a partir das estrelas e atividade; não é a classificação oficial selfh.st.'},
 es:{tab:'Catálogo de apps',search:'Buscar también en repositorios públicos de GitHub…',updated:'Actividad reciente',popular:'Populares',name:'Nombre A–Z',loading:'Cargando catálogo selfh.st…',error:'Catálogo no disponible: ',none:'Sin resultados. Busca en GitHub o pega una URL.',source:'selfh.st y búsqueda GitHub; analizar antes de instalar.',website:'Web ↗',repo:'Repositorio ↗',use:'Analizar',count:'apps',all:'Todas las categorías',stale:'Catálogo en caché.',idle:'Escribe dos caracteres para buscar también en GitHub. Se muestran todas las apps selfh.st.',searching:'Buscando en GitHub…',matches:'Resultados GitHub',limited:'GitHub limita a 1.000 resultados. Refina la búsqueda.',moreGithub:'Más resultados GitHub',githubFail:'Búsqueda GitHub no disponible:',githubGroup:'GitHub – proyectos adicionales',selfhstGroup:'selfh.st – catálogo completo',archived:'Archivado',fork:'Fork',noRepo:'Sin repositorio',tabPopular:'Populares',tabTrending:'Tendencias',tabNew:'Novedades',trendExplanation:'Tendencia estimada según estrellas y actividad; no es la clasificación oficial de selfh.st.'}
};
const sl=k=>(selfhstAppLabels[lang]||selfhstAppLabels.de)[k];

const imCatalogModeText={
 de:{selfhstSearch:'selfh.st-Apps durchsuchen…',githubSearch:'GitHub-Repositories suchen (mindestens 2 Zeichen)…',githubStart:'Mindestens zwei Zeichen eingeben, um öffentliche GitHub-Repositories zu suchen.',githubResults:'GitHub-Repositories',githubOnly:'Nur GitHub-Suchergebnisse; Installation erst nach Quellenanalyse.',selfhstOnly:'Nur selfh.st-Katalog; Installation erst nach Quellenanalyse.',githubNone:'Keine GitHub-Treffer gefunden.',selfhstNone:'Keine Apps im selfh.st-Katalog gefunden.'},
 en:{selfhstSearch:'Search selfh.st apps…',githubSearch:'Search GitHub repositories (2+ characters)…',githubStart:'Enter at least two characters to search public GitHub repositories.',githubResults:'GitHub repositories',githubOnly:'GitHub results only; analyze sources before installing.',selfhstOnly:'selfh.st directory only; analyze sources before installing.',githubNone:'No GitHub repositories found.',selfhstNone:'No apps found in the selfh.st directory.'},
 fr:{selfhstSearch:'Chercher des apps sur selfh.st…',githubSearch:'Chercher des dépôts GitHub (2 caractères minimum)…',githubStart:'Saisissez au moins deux caractères pour chercher sur GitHub.',githubResults:'Dépôts GitHub',githubOnly:'Résultats GitHub uniquement; analyse avant installation.',selfhstOnly:'Catalogue selfh.st uniquement; analyse avant installation.',githubNone:'Aucun dépôt GitHub.',selfhstNone:'Aucune app dans selfh.st.'},
 pt:{selfhstSearch:'Pesquisar apps selfh.st…',githubSearch:'Pesquisar repositórios GitHub (mín. 2 caracteres)…',githubStart:'Introduza pelo menos dois caracteres para pesquisar no GitHub.',githubResults:'Repositórios GitHub',githubOnly:'Apenas resultados GitHub; analisar antes da instalação.',selfhstOnly:'Apenas catálogo selfh.st; analisar antes da instalação.',githubNone:'Nenhum repositório GitHub.',selfhstNone:'Nenhuma app no selfh.st.'},
 es:{selfhstSearch:'Buscar apps selfh.st…',githubSearch:'Buscar repositorios GitHub (mín. 2 caracteres)…',githubStart:'Escribe al menos dos caracteres para buscar en GitHub.',githubResults:'Repositorios GitHub',githubOnly:'Solo resultados GitHub; analizar antes de instalar.',selfhstOnly:'Solo catálogo selfh.st; analizar antes de instalar.',githubNone:'Sin repositorios GitHub.',selfhstNone:'Sin apps en selfh.st.'}
};
const imcl=k=>(imCatalogModeText[lang]||imCatalogModeText.de)[k];
function imCatalogIsGitHub(){return imStoreProvider==='github';}
function imCatalogCancelSearch(){
 if(selfhstAppsSearchTimer)clearTimeout(selfhstAppsSearchTimer);
 selfhstAppsSearchTimer=null;
 ++selfhstAppsSearchSeq;
 selfhstAppsRemoteQuery='';selfhstAppsRemoteRows=[];selfhstAppsRemotePage=0;
 selfhstAppsRemoteTotal=0;selfhstAppsRemoteMore=false;
 selfhstAppsRemoteBusy=false;selfhstAppsRemoteError='';
}

function selfhstAppsTranslate(){
 // The directory is now a provider inside the App-Kataloge tab.
 const isGithub=imCatalogIsGitHub();
 $('#selfhstAppsBrowser').dataset.provider=isGithub?'github':'selfhst';
 $('#selfhstAppsSearch').placeholder=imcl(isGithub?'githubSearch':'selfhstSearch');
 $('#selfhstAppsTag').hidden=isGithub;
 $('#selfhstAppsStatus').hidden=isGithub;
 $('#selfhstAppsGitHubStatus').hidden=!isGithub;
 $('#imSelfhstDirectoryLinks').hidden=isGithub;
 $('#imGitHubDirectoryLinks').hidden=!isGithub;
 $('#imSelfhstCatalogNote').hidden=isGithub;
 $('#imGitHubCatalogNote').hidden=!isGithub;
 const labels={popular:'tabPopular',trending:'tabTrending',new:'tabNew',updated:'updated',name:'name'};
 $$('.im-selfhst-sort-tab').forEach(btn=>btn.textContent=sl(labels[btn.dataset.catalogSort]));
 selfhstAppsUpdateSortTabs();
 const all=$('#selfhstAppsTag option[value=""]');if(all)all.textContent=sl('all');
 $('#selfhstAppsGitHubMore').textContent=sl('moreGithub');
}
function selfhstAppsUpdateSortTabs(){
 const current=selfhstAppsSortMode;
 $$('.im-selfhst-sort-tab').forEach(btn=>{
  const selected=btn.dataset.catalogSort===current;
  btn.classList.toggle('is-active',selected);
  btn.setAttribute('aria-pressed',String(selected));
 });
}
function selfhstAppsSortBy(mode,items){
 const days=value=>{
  const millis=Date.parse(String(value||'')+'T12:00:00Z');
  return Number.isFinite(millis)?Math.max(0,(Date.now()-millis)/86400000):10000;
 };
 const trend=x=>{
  // Estimate current interest, NOT a claim about GitHub star growth.
  const stars=Math.max(0,Number(x.stars)||0);
  return Math.log2(2+stars)*Math.exp(-days(x.updated)/90);
 };
 const compare=(a,b)=>a.name.localeCompare(b.name);
 if(mode==='popular')items.sort((a,b)=>(b.stars||0)-(a.stars||0)||compare(a,b));
 else if(mode==='trending')items.sort((a,b)=>trend(b)-trend(a)||compare(a,b));
 else if(mode==='new')items.sort((a,b)=>(b.new_rank||b.catalog_id||0)-(a.new_rank||a.catalog_id||0)||compare(a,b));
 else if(mode==='name')items.sort(compare);
 else items.sort((a,b)=>(b.updated||'').localeCompare(a.updated||'')||compare(a,b));
 return items;
}
async function loadSelfhstApps(){
 if(imCatalogIsGitHub())return;
 selfhstAppsTranslate();
 if(selfhstApps){renderSelfhstApps();return;}
 if(selfhstAppsLoading)return selfhstAppsLoading;
 $('#selfhstAppsStatus').textContent=sl('loading');
 selfhstAppsLoading=(async()=>{
  try{
   const data=await request('/api/selfhst/apps');selfhstApps=Array.isArray(data.apps)?data.apps:[];
   const tagCounts=new Map();for(const app of selfhstApps){for(const tag of (app.tags||[]))tagCounts.set(tag,(tagCounts.get(tag)||0)+1)}
   const tagSelect=$('#selfhstAppsTag');tagSelect.replaceChildren();
   const empty=document.createElement('option');empty.value='';empty.textContent=sl('all');tagSelect.appendChild(empty);
   for(const [tag] of [...tagCounts].sort((a,b)=>a[0].localeCompare(b[0]))){const op=document.createElement('option');op.value=tag;op.textContent=tag;tagSelect.appendChild(op)}
   $('#selfhstAppsBrowser').dataset.stale=data.stale?'true':'false';selfhstAppsCatalogError='';
  }catch(e){selfhstApps=[];selfhstAppsCatalogError=errorMessage(e);}
  finally{selfhstAppsLoading=null;renderSelfhstApps();}
 })();return selfhstAppsLoading;
}
function selfhstAppsRepoSupported(u){
 try{const x=new URL(u);return x.protocol==='https:'&&!!x.hostname&&x.pathname.split('/').filter(Boolean).length>=2}
 catch(e){return false}
}
function selfhstAppsRepoKey(u){
 try{const x=new URL(u);return x.hostname.toLowerCase()+x.pathname.replace(/\.git$/i,'').replace(/\/$/,'').toLowerCase()}
 catch(e){return ''}
}
function selfhstAppsQueueGitHub(){
 if(!imCatalogIsGitHub()){renderSelfhstApps();return;}
 imCatalogCancelSearch();
 const q=$('#selfhstAppsSearch').value.trim();
 renderSelfhstApps();
 if(q.length<2)return;
 const sequence=selfhstAppsSearchSeq;
 selfhstAppsSearchTimer=setTimeout(()=>selfhstAppsLoadGitHub(q,1,sequence),650);
}

async function selfhstAppsLoadGitHub(q,page,sequence){
 if(!imCatalogIsGitHub()||selfhstAppsRemoteBusy||sequence!==selfhstAppsSearchSeq)return;
 selfhstAppsRemoteBusy=true;selfhstAppsRemoteError='';renderSelfhstApps();
 try{
  const response=await request('/api/apps/github-search?q='+encodeURIComponent(q)+'&page='+page);
  if(sequence!==selfhstAppsSearchSeq)return;
  selfhstAppsRemoteQuery=q;
  const seen=new Set(selfhstAppsRemoteRows.map(x=>selfhstAppsRepoKey(x.repository)));
  for(const x of (response.apps||[])){
   const key=selfhstAppsRepoKey(x.repository);
   if(key&&!seen.has(key)){selfhstAppsRemoteRows.push(x);seen.add(key)}
  }
  selfhstAppsRemotePage=response.page||page;
  selfhstAppsRemoteTotal=response.total_count||0;
  selfhstAppsRemoteMore=!!response.has_more;
 }catch(e){if(sequence!==selfhstAppsSearchSeq)return;selfhstAppsRemoteError=errorMessage(e);}
 finally{if(sequence===selfhstAppsSearchSeq){selfhstAppsRemoteBusy=false;renderSelfhstApps();}}
}
function selfhstAppsMoreGitHub(){
 const q=$('#selfhstAppsSearch').value.trim();
 if(q.length>=2&&selfhstAppsRemoteMore&&!selfhstAppsRemoteBusy&&selfhstAppsRemoteQuery===q){
  selfhstAppsLoadGitHub(q,selfhstAppsRemotePage+1,selfhstAppsSearchSeq);
 }
}
function renderSelfhstApps(){
 const list=$('#selfhstAppsList');list.replaceChildren();
 const isGithub=imCatalogIsGitHub();
 const q=$('#selfhstAppsSearch').value.trim().toLocaleLowerCase();
 const cat=$('#selfhstAppsTag').value;
 const local=(isGithub?[]:(selfhstApps||[])).filter(v=>(!cat||(v.tags||[]).includes(cat))&&(!q||[v.name,v.description,v.slug,v.source,v.repository,...(v.tags||[])].join(' ').toLocaleLowerCase().includes(q)));
 const sort=selfhstAppsSortMode;
 selfhstAppsSortBy(sort,local);
 selfhstAppsUpdateSortTabs();
 const localKeys=new Set(local.map(a=>selfhstAppsRepoKey(a.repository)).filter(Boolean));
 const remote=isGithub?selfhstAppsRemoteRows.filter(a=>!localKeys.has(selfhstAppsRepoKey(a.repository))):[];
 if(isGithub){
  if(sort==='new')remote.sort((a,b)=>(b.created||'').localeCompare(a.created||'')||(b.updated||'').localeCompare(a.updated||''));
  else selfhstAppsSortBy(sort,remote);
 }
 $('#selfhstAppsStatus').textContent=local.length+' '+sl('count')+' · '+imcl('selfhstOnly')+
  (sort==='trending'?' · '+sl('trendExplanation'):'')+
  (selfhstAppsCatalogError?' '+sl('error')+selfhstAppsCatalogError:'')+
  ($('#selfhstAppsBrowser').dataset.stale==='true'?' '+sl('stale'):'');
 const remoteStatus=$('#selfhstAppsGitHubStatus');
 if(q.length<2){remoteStatus.textContent=imcl('githubStart')}
 else if(selfhstAppsRemoteBusy){remoteStatus.textContent=sl('searching')+' '+selfhstAppsRemoteRows.length+' '+sl('matches')}
 else if(selfhstAppsRemoteError){remoteStatus.textContent=sl('githubFail')+' '+selfhstAppsRemoteError}
 else if(selfhstAppsRemoteQuery){remoteStatus.textContent=selfhstAppsRemoteRows.length+' / '+selfhstAppsRemoteTotal+' '+imcl('githubResults')+' · '+imcl('githubOnly')+(selfhstAppsRemoteTotal>1000?' · '+sl('limited'):'')}
 else{remoteStatus.textContent=sl('searching')}
 const frag=document.createDocumentFragment();
 function addTitle(label){const h=document.createElement('h3');h.className='im-catalog-group-title';h.textContent=label;frag.appendChild(h)}
 function addEntry(item){
  const card=document.createElement('article');card.className='im-selfhst-app';
  const head=document.createElement('div');head.className='im-selfhst-app-head';
  const emblem=document.createElement('span');emblem.className='im-selfhst-app-icon';emblem.textContent=(item.name||'?').slice(0,1).toUpperCase();
  if(/^https:\/\/[a-z0-9.\-]+\//i.test(item.icon_url||'')){
   const img=document.createElement('img');img.alt='';img.loading='lazy';img.referrerPolicy='no-referrer';img.src=item.icon_url;
   img.onerror=()=>{
    if(item.icon_png_url&&img.src!==item.icon_png_url){img.src=item.icon_png_url;return}
    img.remove();emblem.textContent=(item.name||'?').slice(0,1).toUpperCase();
   };
   emblem.textContent='';emblem.appendChild(img)
  }
  const titleWrap=document.createElement('div');const title=document.createElement('strong');title.textContent=item.name;
  const sub=document.createElement('span');sub.className='im-selfhst-app-sub';sub.textContent=[item.source,item.updated?sl('updated')+': '+item.updated:'',item.stars?'★ '+item.stars.toLocaleString():''].filter(Boolean).join(' · ');
  titleWrap.append(title,sub);head.append(emblem,titleWrap);
  const desc=document.createElement('p');desc.className='im-selfhst-app-desc';desc.textContent=item.description||'—';
  const tags=document.createElement('div');tags.className='im-selfhst-app-tags';tags.textContent=(item.tags||[]).slice(0,4).join(' · ');
  if(item.archived||item.fork){const flag=document.createElement('span');flag.className='im-selfhst-app-flag';flag.textContent=[item.archived?sl('archived'):'',item.fork?sl('fork'):''].filter(Boolean).join(' · ');tags.append(' ',flag)}
  const actions=document.createElement('div');actions.className='im-selfhst-app-actions';
  for(const [url,label] of [[item.website,sl('website')],[item.repository,sl('repo')]]){
   if(!url||!/^https:\/\//.test(url))continue;
   const link=document.createElement('a');link.textContent=label;link.href=url;link.target='_blank';link.rel='noopener noreferrer';actions.appendChild(link);
  }
  if(selfhstAppsRepoSupported(item.repository)){
   const btn=document.createElement('button');btn.type='button';btn.textContent=sl('use');btn.onclick=()=>{
    if(busy)return;
    setSourceType('url');$('#sourceInput').value=item.repository;showSourceDiagnosis(null);
    // Reads the publisher's Compose and validates it. Never installs anything.
    void analyze();
   };actions.appendChild(btn);
  }
  card.append(head,desc,tags,actions);frag.appendChild(card);
 }
 // GitHub search ranking is already ordered by the GitHub API and should not
 // be re-sorted by timestamps. Never discard repos lacking Docker evidence.
 if(remote.length){addTitle(imcl('githubResults')+' ('+remote.length+')');for(const x of remote)addEntry(x)}
 if(local.length){addTitle(sl('selfhstGroup')+' ('+local.length+')');for(const x of local)addEntry(x)}
 list.appendChild(frag);
 if(!remote.length&&!local.length&&!selfhstAppsRemoteBusy){
  const noResults=isGithub?(q.length<2?'':imcl('githubNone')):imcl('selfhstNone');
  if(noResults)list.textContent=noResults;
 }
 const more=$('#selfhstAppsGitHubMore');more.hidden=!(isGithub&&selfhstAppsRemoteMore&&q.length>=2);
 more.disabled=!!selfhstAppsRemoteBusy;
 more.textContent=sl('moreGithub');
}

// v0.2.54 – Preserve source-authored ZimaOS app metadata in each available language.
let imStoreProvider='mine',imMyStoreApps=null,imMyStoreLoad=null,imMyStoreStatus='';
const imStoreLanguage={
 de:{title:'App-Kataloge',subtitle:'Quelle auswählen – jede App wird vor der Installation geprüft.',search:'Meine Apps durchsuchen…',refresh:'Aktualisieren',loading:'iSanto1306 Apps werden geladen…',loadError:'Katalog konnte nicht geladen werden: ',count:'verfügbare App-Vorlagen',fallback:'Nur zuletzt bestätigte Quellpfade; GitHub derzeit nicht vollständig geprüft.',cached:'Zwischengespeicherte Liste.',analyze:'Konfigurieren →',none:'Keine passenden Apps gefunden.',lsio:'Ausgewähltes Image konfigurieren →'},
 en:{title:'App catalogs',subtitle:'Choose a source; every app is checked before installation.',search:'Search my apps…',refresh:'Refresh',loading:'Loading iSanto1306 Apps…',loadError:'Catalog unavailable: ',count:'available app templates',fallback:'Last verified source paths only; GitHub is not fully verified now.',cached:'Cached list.',analyze:'Configure →',none:'No matching apps.',lsio:'Configure selected image →'},
 fr:{title:'Catalogues d’apps',subtitle:'Choisir une source; vérification avant installation.',search:'Rechercher mes apps…',refresh:'Actualiser',loading:'Chargement des apps…',loadError:'Catalogue indisponible : ',count:'modèles disponibles',fallback:'Liens vérifiés précédemment.',cached:'En cache.',analyze:'Configurer →',none:'Aucune app correspondante.',lsio:'Configurer l’image →'},
 pt:{title:'Catálogos de aplicações',subtitle:'Escolher uma fonte; verificar antes de instalar.',search:'Pesquisar as minhas apps…',refresh:'Atualizar',loading:'A carregar aplicações…',loadError:'Catálogo indisponível: ',count:'modelos disponíveis',fallback:'Caminhos anteriormente verificados.',cached:'Em cache.',analyze:'Configurar →',none:'Sem aplicações.',lsio:'Configurar imagem →'},
 es:{title:'Catálogos de aplicaciones',subtitle:'Elige la fuente; revisión antes de instalar.',search:'Buscar mis apps…',refresh:'Actualizar',loading:'Cargando aplicaciones…',loadError:'Catálogo no disponible: ',count:'plantillas disponibles',fallback:'Rutas verificadas anteriormente.',cached:'En caché.',analyze:'Configurar →',none:'Ninguna app.',lsio:'Configurar imagen →'}
};
const imsw=k=>(imStoreLanguage[lang]||imStoreLanguage.de)[k];
// ZimaOS Compose x-casaos.tagline supports locale-keyed descriptions.
// Select the active UI language and prefer English if a particular locale is
// not available. Never translate arbitrary repository text without a source.
const imStoreLocales={de:'de_DE',en:'en_US',fr:'fr_FR',pt:'pt_PT',es:'es_ES'};
function imStoreDescription(app){
 const versions=app.description_i18n||{};
 return versions[imStoreLocales[lang]]||versions[lang]||versions.en_US||versions.de_DE||app.description||'';
}
function imStoreCategory(category){
 if(!category)return '';
 const values={Others:'categoryOthers',Developer:'categoryDeveloper',Productivity:'categoryProductivity',Media:'categoryMedia',Home:'categoryHome',Networking:'categoryNetworking',Finance:'categoryFinance',AI:'categoryAI',Social:'categorySocial'};
 return values[category] ? ux(values[category]) : category;
}

function imStoresTranslate(){
 const t=$('[data-kind="stores"]');if(t)t.textContent=imsw('title');
 $('#imStoresTitle').textContent=imsw('title');$('#imStoresSubtitle').textContent=imsw('subtitle');
 $('#imStoresMySearch').placeholder=imsw('search');$('#imStoresRefresh').textContent=imsw('refresh');
 $('#imStoresLsioAnalyze').textContent=imsw('lsio');
 if(imMyStoreApps)imRenderMyStore();
}
function imChangeStoreProvider(provider){
 if(!['mine','linuxserver','selfhst','github'].includes(provider))return;
 if(imStoreProvider!==provider){
  imCatalogCancelSearch();
  $('#selfhstAppsSearch').value='';
  $('#selfhstAppsTag').value='';
 }
 imStoreProvider=provider;
 $$('.im-store-provider').forEach(b=>{
  const selected=b.dataset.storeProvider===provider;
  b.classList.toggle('is-active',selected);b.setAttribute('aria-pressed',String(selected));
 });
 setSourceType('stores');
}
async function imLoadMyStore(force=false){
 if(force){imMyStoreApps=null;imMyStoreStatus='';}
 if(imMyStoreApps){imRenderMyStore();return}
 if(imMyStoreLoad)return imMyStoreLoad;
 $('#imStoresMineStatus').textContent=imsw('loading');
 imMyStoreLoad=(async()=>{
  try{
   const data=await request('/api/app-stores/isanto1306');
   imMyStoreApps=Array.isArray(data.apps)?data.apps:[];
   imMyStoreStatus=data.origin||'';
  }catch(e){imMyStoreApps=[];imMyStoreStatus=imsw('loadError')+errorMessage(e)}
  finally{imMyStoreLoad=null;imRenderMyStore()}
 })();return imMyStoreLoad;
}
function imRenderMyStore(){
 const list=$('#imStoresMineList');list.replaceChildren();
 const q=$('#imStoresMySearch').value.toLocaleLowerCase().trim();
 const matches=(imMyStoreApps||[]).filter(x=>!q||[x.id,x.name,imStoreDescription(x),imStoreCategory(x.category)].join(' ').toLocaleLowerCase().includes(q));
 let status=matches.length+' '+imsw('count');
 if(imMyStoreStatus==='verified-fallback')status+=' · '+imsw('fallback');
 else if(imMyStoreStatus==='cached')status+=' · '+imsw('cached');
 else if(imMyStoreStatus&&imMyStoreStatus!=='github-source')status+=' · '+imMyStoreStatus;
 $('#imStoresMineStatus').textContent=status;
 for(const app of matches){
  const card=document.createElement('article');card.className='im-selfhst-app';
  const head=document.createElement('div');head.className='im-selfhst-app-head';
  const icon=document.createElement('span');icon.className='im-selfhst-app-icon';icon.textContent=(app.name||'?').charAt(0);
  if(/^https:\/\/[a-z0-9.-]+\//i.test(app.icon_url||'')){
   const img=document.createElement('img');img.alt='';img.loading='lazy';img.referrerPolicy='no-referrer';
   img.onerror=()=>{img.remove();icon.textContent=(app.name||'?').charAt(0)};img.src=app.icon_url;
   icon.textContent='';icon.appendChild(img);
  }
  const label=document.createElement('div');const name=document.createElement('strong');name.textContent=app.name;
  const sub=document.createElement('span');sub.className='im-selfhst-app-sub';sub.textContent='iSanto1306 Apps · '+imStoreCategory(app.category);
  label.append(name,sub);head.append(icon,label);
  const desc=document.createElement('p');desc.className='im-selfhst-app-desc';desc.textContent=imStoreDescription(app);
  const actions=document.createElement('div');actions.className='im-selfhst-app-actions';
  const link=document.createElement('a');link.textContent=sl('repo');link.href=app.source_url;link.target='_blank';link.rel='noopener noreferrer';actions.appendChild(link);
  const btn=document.createElement('button');btn.type='button';btn.textContent=imsw('analyze');
  btn.onclick=()=>{
   if(busy)return;
   setSourceType('url');$('#sourceInput').value=app.compose_url;showSourceDiagnosis(null);void analyze();
  };
  actions.append(btn);card.append(head,desc,actions);list.append(card);
 }
 if(!matches.length){const empty=document.createElement('p');empty.className='field-note';empty.textContent=imsw('none');list.append(empty)}
}

const resourceWords={
 de:{heading:'NAS-Hardware und Ressourcen',refresh:'Hardware erkennen',loading:'NAS-Hardware wird geprüft …',unknown:'CPU/RAM unbekannt',unavailable:'GPU-Erkennung fehlgeschlagen – keine neue GPU-Freigabe möglich.',gpuNone:'Keine zusätzliche GPU-Freigabe',limitDefault:'Originalwert beibehalten',ram:'RAM-Limit (MB)',cpu:'CPU-Limit (logische CPUs)',gpu:'Hardwarebeschleunigung',appNote:'GPU-Zuweisung aktiviert nur Gerätezugriff. Die App muss VAAPI, CUDA oder NVENC selbst unterstützen.',all:'Keine GPU gefunden oder noch nicht geprüft',label:'NAS',warn:'Die Erkennung ermittelt Geräte, nicht automatisch die App-Kompatibilität.'},
 en:{heading:'NAS hardware and resources',refresh:'Detect hardware',loading:'Inspecting NAS hardware …',unknown:'CPU/RAM unavailable',unavailable:'GPU probing failed – cannot grant new GPU access.',gpuNone:'No additional GPU access',limitDefault:'Keep original value',ram:'RAM limit (MB)',cpu:'CPU limit (logical CPUs)',gpu:'Hardware acceleration',appNote:'GPU access only exposes devices; the application itself must support VAAPI, CUDA or NVENC.',all:'No GPU found or not yet checked',label:'NAS',warn:'Detects hardware, not per-app compatibility.'},
 pt:{heading:'Hardware e recursos do NAS',refresh:'Detetar hardware',loading:'A verificar hardware do NAS …',unknown:'CPU/RAM indisponível',unavailable:'Deteção de GPU falhou – sem acesso novo à GPU.',gpuNone:'Sem acesso adicional à GPU',limitDefault:'Manter valor original',ram:'Limite de RAM (MB)',cpu:'Limite de CPU (CPUs lógicas)',gpu:'Aceleração por hardware',appNote:'A aplicação deve suportar VAAPI, CUDA ou NVENC.',all:'GPU não detetada ou ainda não verificada',label:'NAS',warn:'A deteção não comprova compatibilidade da aplicação.'},
 fr:{heading:'Matériel et ressources du NAS',refresh:'Détecter le matériel',loading:'Analyse du matériel NAS …',unknown:'CPU/RAM inconnus',unavailable:'Détection GPU impossible – aucun nouvel accès GPU.',gpuNone:'Aucun accès GPU supplémentaire',limitDefault:'Conserver la valeur initiale',ram:'Limite RAM (Mo)',cpu:'Limite CPU (CPU logiques)',gpu:'Accélération matérielle',appNote:'L’application doit prendre en charge VAAPI, CUDA ou NVENC.',all:'Aucun GPU trouvé ou non détecté',label:'NAS',warn:'La détection ne valide pas la compatibilité de l’application.'},
 es:{heading:'Hardware y recursos del NAS',refresh:'Detectar hardware',loading:'Analizando hardware del NAS …',unknown:'CPU/RAM desconocidos',unavailable:'No se detecta la GPU: no se concede acceso nuevo.',gpuNone:'Sin acceso GPU adicional',limitDefault:'Conservar valor original',ram:'Límite RAM (MB)',cpu:'Límite CPU (CPU lógicas)',gpu:'Aceleración por hardware',appNote:'La aplicación debe admitir VAAPI, CUDA o NVENC.',all:'GPU no encontrada o sin comprobar',label:'NAS',warn:'La detección no garantiza compatibilidad de la aplicación.'}
};
const rw=k=>(resourceWords[lang]||resourceWords.de)[k];
let hostHardware=null;
const timezoneWords={
 de:['Zeitzone','Erneut erkennen','Originalwert behalten','Automatisch – NAS-Zeitzone übernehmen','Manuell auswählen','Zeitzone (IANA)','TZ bei Diensten ohne eigene TZ-Angabe zusätzlich eintragen','NAS-Zeitzone','Original','Keine TZ im Original','NAS-Zeitzone nicht sicher erkannt. Manuell wählen oder Original behalten.','Vorhandene TZ-Werte werden nicht ohne deine Auswahl verändert.','Neue TZ-Variablen werden nur nach deiner Bestätigung eingetragen.'],
 en:['Time zone','Detect again','Keep original value','Automatic – use NAS time zone','Choose manually','Time zone (IANA)','Also add TZ to services without TZ','NAS time zone','Original','No TZ in original','NAS time zone could not be verified. Choose manually or keep original.','Original TZ values are not changed without your selection.','New TZ values are added only if you opt in.'],
 pt:['Fuso horário','Detetar novamente','Manter valor original','Automático – usar fuso do NAS','Escolher manualmente','Fuso horário (IANA)','Adicionar TZ aos serviços sem TZ','Fuso do NAS','Original','Sem TZ no original','Não foi possível verificar o fuso do NAS. Escolha manualmente ou mantenha o original.','Os valores TZ originais não são alterados sem a sua escolha.','Só são adicionados novos TZ com consentimento.'],
 fr:['Fuseau horaire','Détecter à nouveau','Conserver la valeur initiale','Automatique – fuseau du NAS','Choisir manuellement','Fuseau horaire (IANA)','Ajouter TZ aux services sans TZ','Fuseau NAS','Original','Pas de TZ dans l’original','Fuseau NAS non vérifié. Choisir manuellement ou conserver la valeur initiale.','Le TZ original reste intact sans votre choix.','De nouvelles variables TZ ne sont ajoutées que sur demande.'],
 es:['Zona horaria','Detectar de nuevo','Conservar valor original','Automático – usar zona del NAS','Elegir manualmente','Zona horaria (IANA)','Añadir TZ a servicios sin TZ','Zona del NAS','Original','Sin TZ original','No se ha podido verificar la zona del NAS. Selecciona manualmente o conserva el original.','Los valores TZ existentes se conservan si no eliges cambiarlos.','Solo se añaden valores TZ nuevos con tu consentimiento.']
};
let timezoneInfo=null, timezoneTouched=false;
function selectedTimezoneMode(){return document.querySelector('input[name="timezoneMode"]:checked')?.value||'original';}
function setTimezoneMode(value){const el=document.querySelector('input[name="timezoneMode"][value="'+value+'"]');if(el)el.checked=true;renderTimezone();}
function renderTimezone(){
 const w=timezoneWords[lang]||timezoneWords.de;
 ['timezoneHeading','timezoneRefresh','timezoneOriginalLabel','timezoneNasLabel','timezoneManualLabel','timezoneNameLabel','timezoneMissingLabel'].forEach((id,i)=>$('#'+id).textContent=w[i]);
 const original=timezoneInfo?.original||{};const existing=Object.entries(original);
 const src=existing.length?existing.map(([name,tz])=>name+': '+tz).join(' · '):w[9];
 const nas=timezoneInfo?.host_timezone||'';
 $('#timezoneStatus').textContent=w[7]+': '+(nas||'—')+' · '+w[8]+': '+src;
 const nasRadio=document.querySelector('input[name="timezoneMode"][value="nas"]');nasRadio.disabled=!nas;
 if(!nas&&selectedTimezoneMode()==='nas')setTimezoneMode('original');
 const mode=selectedTimezoneMode();const manual=mode==='manual';$('#timezoneManualRow').hidden=!manual;$('#timezoneAddMissing').disabled=mode==='original';
 const opts=$('#timezoneName');const current=opts.value||'Europe/Berlin';
 if(timezoneInfo?.timezones?.length&&!opts.dataset.loaded){
  opts.replaceChildren();for(const tz of timezoneInfo.timezones){const option=document.createElement('option');option.value=tz;option.textContent=tz;opts.appendChild(option)}opts.dataset.loaded='yes';
  opts.value=[...opts.options].some(o=>o.value===current)?current:(nas||'Europe/Berlin');
 }
 $('#timezoneDetails').textContent=(!nas?w[10]+' ':'')+w[11]+' '+w[12];
}
async function loadTimezone(reset=false){
 const generation=wizardGeneration;
 if(reset){timezoneTouched=false;timezoneInfo=null;$('#timezoneAddMissing').checked=false;$('#timezoneName').dataset.loaded='';}
 try{
  const response=await request('/api/timezone/inspect',{source:$('#sourceYaml').value});if(generation!==wizardGeneration)return;timezoneInfo=response;
  if(!timezoneTouched){setTimezoneMode(Object.keys(response.original||{}).length?'original':response.host_detected?'nas':'original');}
 }catch(e){if(generation!==wizardGeneration)return;timezoneInfo={host_timezone:'',original:{},timezones:[]};if(!timezoneTouched)setTimezoneMode('original');$('#timezoneDetails').textContent=errorMessage(e);}
 renderTimezone();
}
function configuredTimezone(){return {timezone_mode:selectedTimezoneMode(),timezone_name:$('#timezoneName').value||'',timezone_add_missing:$('#timezoneAddMissing').checked};}
function configuredResources(){
 const choices={};
 for(const row of document.querySelectorAll('#resourceServiceList .im-resource-service')){
  const name=row.dataset.service;
  const mem=row.querySelector('.im-mem').value.trim();
  const cpu=row.querySelector('.im-cpu').value.trim();
  const gpu=row.querySelector('.im-gpu').value;
  if(mem||cpu||gpu!=='none')choices[name]={memory_mb:mem?Number(mem):null,cpu_cores:cpu?Number(cpu):null,gpu};
 }
 return choices;
}
function renderResources(preserve=true){
 const w=resourceWords[lang]||resourceWords.de;
 const chosen=preserve?configuredResources():{};
 $('#resourceHeading').textContent=w.heading;$('#hardwareRefresh').textContent=w.refresh;
 $('#hardwareCaution').textContent=w.appNote+' '+w.warn;
 const systemTexts={
  de:['Zielsystem','ZimaOS (direkte Installation)','CasaOS (YAML-Export)','Docker Compose / Portainer (YAML-Export)','ZimaOS ist vorausgewählt. Andere Zielsysteme erzeugen nur die YAML-Datei.'],
  en:['Target platform','ZimaOS (install)','CasaOS (YAML export)','Docker Compose / Portainer (YAML export)','ZimaOS is the default. Other platforms support YAML export only.'],
  fr:['Système cible','ZimaOS (installation)','CasaOS (export YAML)','Docker Compose / Portainer (export YAML)','ZimaOS est sélectionné par défaut. Les autres plateformes ne permettent que l’export YAML.'],
  pt:['Sistema de destino','ZimaOS (instalação)','CasaOS (exportar YAML)','Docker Compose / Portainer (exportar YAML)','ZimaOS é a opção predefinida. Os restantes destinos permitem apenas exportar YAML.'],
  es:['Sistema de destino','ZimaOS (instalación)','CasaOS (exportar YAML)','Docker Compose / Portainer (exportar YAML)','ZimaOS está seleccionado por defecto. Los demás destinos solo permiten exportar YAML.']
 };
 const tw=systemTexts[lang]||systemTexts.de;
 $('#imTargetSystemLabel').textContent=tw[0];
 $('#imTargetSystem').options[0].textContent=tw[1];
 $('#imTargetSystem').options[1].textContent=tw[2];
 $('#imTargetSystem').options[2].textContent=tw[3];
 $('#imTargetSystemHelp').textContent=tw[4];
 const summary=$('#hardwareSummary');const hw=hostHardware;
 const gpus=Array.isArray(hw?.gpus)?hw.gpus:[];
 if(!hw)summary.textContent=w.loading;
 else summary.textContent=(hw.cpu_threads?hw.cpu_threads+' CPU-Threads':'CPU ?')+' · '+(hw.memory_mb?Math.round(hw.memory_mb/1024)+' GB RAM':'RAM ?')+' · '+(gpus.length?gpus.map(g=>g.name+(g.available?' ✓':' –')).join(', '):w.all)+(hw.warning?' · '+w.unavailable:'');
 let services={};try{services=window.jsyaml?window.jsyaml.load($('#sourceYaml').value)?.services||{}:{}}catch(e){}
 if(!Object.keys(services).length){
  // Render from source text if js-yaml is unavailable, without executing arbitrary YAML.
  const lines=$('#sourceYaml').value.split(/\r?\n/);let inside=false,depth=null;
  for(const line of lines){
   if(/^services:\s*(?:#.*)?$/.test(line)){inside=true;depth=null;continue}
   if(!inside||!line.trim()||/^\s*#/.test(line))continue;
   const match=line.match(/^([ \t]+)([a-zA-Z0-9_-]+):\s*(?:#.*)?$/);
   if(!/^\s/.test(line)){inside=false;continue}
   if(!match)continue;
   const indent=match[1].replace(/\t/g,'    ').length;
   if(depth===null)depth=indent;
   if(indent===depth)services[match[2]]={};
  }
 }
 const list=$('#resourceServiceList');list.replaceChildren();
 for(const name of Object.keys(services).slice(0,64)){
  const record=chosen[name]||{};
  const wrap=document.createElement('div');wrap.className='im-resource-service';wrap.dataset.service=name;
  const title=document.createElement('strong');title.textContent=name;
  const fields=document.createElement('div');fields.className='im-resource-grid';
  const add=(cls,label,tag,attr,val)=>{const box=document.createElement('div');box.className=cls==='im-gpu'?'im-resource-gpu-field':'';const lab=document.createElement('label');lab.textContent=label;const input=document.createElement(tag);input.className=cls;Object.entries(attr).forEach(([k,v])=>input.setAttribute(k,String(v)));if(val!==undefined&&val!==null)input.value=String(val);box.append(lab,input);fields.appendChild(box);return input};
  add('im-mem',w.ram,'input',{type:'number',min:64,max:hw?.memory_mb||262144,step:64,placeholder:w.limitDefault},record.memory_mb);
  const cpuInput=add('im-cpu',w.cpu,'input',{type:'number',min:1,max:hw?.cpu_threads||1,step:1,placeholder:w.limitDefault},record.cpu_cores);
  cpuInput.disabled=!Number.isInteger(hw?.cpu_threads)||hw.cpu_threads<1;
  cpuInput.addEventListener('change',()=>{if(!cpuInput.value.trim())return;const n=Number(cpuInput.value);if(!Number.isFinite(n)){cpuInput.value='';return;}cpuInput.value=String(Math.max(1,Math.min(hw.cpu_threads,Math.round(n))));});
  const gpuSelect=add('im-gpu',w.gpu,'select',{},'none');
  const none=document.createElement('option');none.value='none';none.textContent=w.gpuNone;gpuSelect.append(none);
  for(const g of gpus){const opt=document.createElement('option');opt.value=g.vendor;opt.textContent=g.name+(g.vendor==='nvidia'?' (CUDA/NVENC)':' (VAAPI)')+(g.available?'':' – '+g.reason);opt.disabled=!g.available;gpuSelect.appendChild(opt);}
  const preferred=record.gpu||'none';if(preferred!=='none'&&gpus.some(g=>g.vendor===preferred&&g.available))gpuSelect.value=preferred;
  if(!hw?.probe_ok)gpuSelect.disabled=true;
  wrap.append(title,fields);list.appendChild(wrap);
 }
}
async function loadHostResources(refresh=false){
 if(!hostHardware)renderResources(true);
 try{hostHardware=await request('/api/hardware'+(refresh?'?refresh=true':''))}catch(e){hostHardware={probe_ok:false,warning:true,gpus:[],cpu_threads:0,memory_mb:0}};
 renderResources(true);
}

let wizardGeneration=0;
let availableProfiles=[];let publisherImages=[];let setupLaterProfiles=new Set();let planReady=false;let lang=localStorage.getItem('installMonitorLanguage')||'en'; if(!languages[lang])lang='en';let csrf='',kind='image',step=1,source='',appName='',busy=false,installed=false;
const newTexts={
 de:{installedDone:'✓ Erfolgreich installiert',readinessReady:'Installationsvoraussetzungen erfüllt',readinessBlocked:'Vor der Installation noch erforderlich',fixSetup:'Zur Konfiguration zurück',technicalSummary:'Technische Hinweise',publishedImage:'Offiziell dokumentiertes Image',publisherAccept:'Dieses Image bewusst übernehmen',publisherApplied:'Veröffentlichtes Image übernommen. Quell-Compose bitte überprüfen.'},
 en:{installedDone:'✓ Successfully installed',readinessReady:'Installation prerequisites met',readinessBlocked:'Required before installation',fixSetup:'Back to configuration',technicalSummary:'Technical notes',publishedImage:'Image documented by publisher',publisherAccept:'Explicitly use this image',publisherApplied:'Published image selected. Please review the source Compose.'},
 fr:{installedDone:'✓ Installé avec succès',readinessReady:'Conditions d’installation remplies',readinessBlocked:'À résoudre avant l’installation',fixSetup:'Retour à la configuration',technicalSummary:'Remarques techniques',publishedImage:'Image documentée par l’éditeur',publisherAccept:'Utiliser explicitement cette image',publisherApplied:'Image publiée sélectionnée. Vérifiez le Compose source.'},
 pt:{installedDone:'✓ Instalação concluída',readinessReady:'Pré-requisitos de instalação cumpridos',readinessBlocked:'Necessário antes da instalação',fixSetup:'Voltar à configuração',technicalSummary:'Notas técnicas',publishedImage:'Imagem documentada pelo autor',publisherAccept:'Usar explicitamente esta imagem',publisherApplied:'Imagem publicada selecionada. Verifique o Compose original.'},
 es:{installedDone:'✓ Instalación completada',readinessReady:'Requisitos de instalación cumplidos',readinessBlocked:'Pendiente antes de instalar',fixSetup:'Volver a la configuración',technicalSummary:'Notas técnicas',publishedImage:'Imagen documentada por el autor',publisherAccept:'Usar expresamente esta imagen',publisherApplied:'Imagen publicada seleccionada. Revise el Compose original.'}
};
const actionTexts={
 de:{enterCloudflare:'Cloudflare-Token eingeben',enterTailscale:'Tailscale-Schlüssel eingeben',usePublisherImage:'Hersteller-Image übernehmen',editSource:'Quell-Compose bearbeiten',needPublisherImage:'Hersteller-Image in der Konfiguration auswählen',actionsHint:'Offene Punkte einzeln beheben. Gewählte Zusatzdienste bleiben ausgewählt.',imageChanged:'Hersteller-Image übernommen. Die verbleibenden Voraussetzungen werden erneut geprüft.'},
 en:{enterCloudflare:'Enter Cloudflare token',enterTailscale:'Enter Tailscale key',usePublisherImage:'Use publisher image',editSource:'Edit source Compose',needPublisherImage:'Choose publisher image in configuration',actionsHint:'Resolve each requirement. Selected services remain selected.',imageChanged:'Publisher image selected. Checking remaining requirements.'},
 fr:{enterCloudflare:'Saisir le jeton Cloudflare',enterTailscale:'Saisir la clé Tailscale',usePublisherImage:'Utiliser l’image officielle',editSource:'Modifier le Compose source',needPublisherImage:'Choisir l’image de l’éditeur dans la configuration',actionsHint:'Résoudre chaque exigence. Les services sélectionnés restent sélectionnés.',imageChanged:'Image choisie. Vérification des conditions restantes.'},
 pt:{enterCloudflare:'Inserir token Cloudflare',enterTailscale:'Inserir chave Tailscale',usePublisherImage:'Usar imagem do autor',editSource:'Editar Compose de origem',needPublisherImage:'Escolher imagem do autor na configuração',actionsHint:'Resolver cada requisito. Serviços selecionados permanecem selecionados.',imageChanged:'Imagem escolhida. A verificar requisitos restantes.'},
 es:{enterCloudflare:'Introducir token Cloudflare',enterTailscale:'Introducir clave Tailscale',usePublisherImage:'Usar imagen del fabricante',editSource:'Editar Compose de origen',needPublisherImage:'Elegir imagen del fabricante en la configuración',actionsHint:'Resolver cada requisito. Los servicios seleccionados siguen seleccionados.',imageChanged:'Imagen seleccionada. Comprobando requisitos restantes.'}
};
const setupLaterTexts={
 de:{label:'Später einrichten',hint:'Der Zusatzdienst wird jetzt installiert. Nur seine Zugangsdaten und Inbetriebnahme folgen später. Bis dahin kann er gestoppt sein oder neu starten.',pending:'Installiert, Einrichtung ausstehend',pendingHeading:'Mitinstallierte Dienste – Einrichtung später',pendingDescription:'Cloudflare und Tailscale bleiben in der Docker-Compose-Konfiguration und werden nicht weggelassen.'},
 en:{label:'Configure later',hint:'Install this additional service now; configure its credentials and activate it later. It may stop or restart until configured.',pending:'Installed, setup pending',pendingHeading:'Installed services – configure later',pendingDescription:'Cloudflare and Tailscale remain in Docker Compose and are not omitted.'},
 fr:{label:'Configurer plus tard',hint:'Ce service est installé maintenant, mais son authentification et sa mise en service attendront. Il peut rester arrêté ou redémarrer.',pending:'Installé, configuration en attente',pendingHeading:'Services installés – configuration ultérieure',pendingDescription:'Cloudflare et Tailscale restent dans Docker Compose.'},
 pt:{label:'Configurar mais tarde',hint:'O serviço é instalado já; credenciais e ativação podem ser configuradas mais tarde. Pode parar ou reiniciar entretanto.',pending:'Instalado, configuração pendente',pendingHeading:'Serviços instalados – configurar depois',pendingDescription:'Cloudflare e Tailscale permanecem no Docker Compose.'},
 es:{label:'Configurar más tarde',hint:'El servicio se instala ahora; sus credenciales y activación se pueden configurar después. Puede detenerse o reiniciarse.',pending:'Instalado, configuración pendiente',pendingHeading:'Servicios instalados – configurar después',pendingDescription:'Cloudflare y Tailscale permanecen en Docker Compose.'}
};
const st=k=>setupLaterTexts[lang]?.[k]||setupLaterTexts.de[k]||k;
const ta=k=>actionTexts[lang]?.[k]||actionTexts.de[k]||k;
const oldT=k=>(languages[lang]||languages.de)[k]||languages.de[k]||k;
const t=k=>newTexts[lang]?.[k]||newTexts.de[k]||oldT(k);
function updateInstallAction(){
 const button=$('#installBtn');if(!button)return;
 button.dataset.t=installed?'installedDone':'installNow';
 button.textContent=t(button.dataset.t);
 button.disabled=busy||installed;
 button.classList.toggle('install-finished',installed);
 button.setAttribute('aria-disabled',String(busy||installed));
}

// v0.2.53: Additional catalog, setup, security, and status translations.
const imExtraTexts={"de":{"sourceImage":"Docker-Image","sourceUrl":"GitHub / URL","sourceYaml":"Compose-YAML","sourceStores":"App-Kataloge","storesSubtitle":"Quellen auswählen und Apps vor der Installation prüfen","mySearch":"Meine Apps durchsuchen…","mySearchLabel":"Eigene Apps suchen","myRepository":"iSanto1306 Apps – Quellrepository ↗","storeManifest":"ZimaOS Store-Manifest ↗","selfhstNote":"Alle selfh.st-Apps werden angezeigt. Die Suche filtert nur diesen Katalog. Nach Auswahl prüft Install Monitor die Installationsvoraussetzungen.","githubNote":"GitHub-Repositories werden erst ab zwei Suchzeichen abgerufen. Nicht jedes Repository enthält eine installierbare Docker-Konfiguration. Die Sortierung bezieht sich nur auf die geladenen Treffer (maximal 1.000 je Suche).","iconFolder":"Ordner wählen","iconPickerTitle":"App-Logos auswählen","iconRescan":"Erneut suchen","iconSearch":"Suchen","iconOrigin":"Logoquelle","iconSearchLabel":"App-Logo suchen","iconSearchHint":"App-Logo suchen …","iconCatalogLink":"selfh.st-Katalog ↗","targetSystem":"Zielsystem","targetHelp":"ZimaOS ist vorausgewählt. Andere Zielsysteme erzeugen nur die YAML-Datei.","targetZima":"ZimaOS (direkte Installation)","targetCasa":"CasaOS (YAML-Export)","targetDocker":"Docker Compose / Portainer (YAML-Export)","gpuCaution":"Limits gelten pro Container. Ein GPU-Gerät wird nur bei ausdrücklicher Auswahl freigegeben. Die App muss VAAPI, CUDA oder NVENC selbst unterstützen.","timezoneHelp":"Vorhandene TZ-Werte werden nur geändert, wenn du eine andere Einstellung auswählst.","proxyTitle":"Authenticator – Reverse Proxy","proxyHelp":"Vor jeder Installation über HTTPS-Reverse-Proxy einen aktuellen sechsstelligen Code eingeben.","proxyCode":"Authenticator-Code","buildConsent":"Ich bestätige, dass Install Monitor den fremden GitHub-Quellcode auf meinem NAS als Docker-Image bauen darf. Dockerfile-Befehle können Code ausführen. Bei privilegierten Anwendungen erhält der spätere Container erweiterten Zugriff auf das NAS.","installProgress":"Installationsverlauf","installEvents":"Protokoll der Installationsschritte","aboutCpu":"CPU-Auslastung","aboutMemory":"Arbeitsspeicher","aboutSince":"Online seit","aboutVersion":"Version","aboutSupport":"Unterstützt von","aboutDonate":"Projekt unterstützen","aboutFooter":"Ressourcenverbrauch des Install-Monitor-Containers","aboutUnavailable":"Nicht verfügbar","aboutDetected":"Erkannt","aboutNotDetected":"Nicht erkannt","aboutNotChecked":"Nicht geprüft","authStatusLoading":"Status wird geladen …","authStart":"Einrichtung starten","authScan":"Authenticator → Plus (+) → Anderes Konto → QR-Code scannen.","authManual":"Stattdessen Einrichtungsschlüssel manuell eingeben","setupKey":"Einrichtungsschlüssel (einmalig)","authConfirmCode":"Sechsstelligen Code bestätigen","authEnable":"Aktivieren","authEnabled":"Aktiviert. Zugelassene Reverse-Proxy-Hosts:","authDisabled":"Noch nicht eingerichtet. Zugelassene Reverse-Proxy-Hosts:","authNone":"keine","authUnset":"keine (IM_ALLOWED_PROXY_HOSTS setzen)","proxyHostsHeading":"Reverse-Proxy-Hosts verwalten","proxyHostsHelp":"Nur HTTPS-Ziele mit gültigem Zertifikat. Die Adresse muss die ZimaOS-API bereitstellen, nicht nur die Install-Monitor-Webseite. Änderungen erfordern Authenticator.","proxyHostname":"Neuen Hostnamen eintragen","proxyChangeCode":"Authenticator-Code für Änderung","proxyAdd":"Host hinzufügen","proxyNoHosts":"Keine Hosts freigegeben.","proxyRemove":"Entfernen","proxyCodeRequired":"Sechsstelligen Authenticator-Code eingeben.","proxyHostInvalid":"Gültigen DNS-Hostnamen ohne https:// eingeben.","proxyHostsUpdated":"Reverse-Proxy-Hosts aktualisiert.","installAuthRequired":"Authenticator-Code eingeben.","installBuildRequired":"Lokalen Build aus fremdem GitHub-Quellcode ausdrücklich bestätigen.","installPreparing":"Installation wird vorbereitet.","installInterrupted":"Live-Verbindung unterbrochen. Die Installation kann auf ZimaOS weiterlaufen. App-Status überprüfen.","scanStartFailed":"GitHub-Scan konnte nicht gestartet werden.","scanNoSource":"Der GitHub-Scan lieferte keine Compose-Quelle.","scanTimeout":"Die GitHub-Analyse dauert zu lange. Bitte GitHub-API-Limit und Container-Logs prüfen. Es wurde nichts installiert.","folderHeading":"NAS-Ordner auswählen","folderBack":"Zurück","folderUse":"Diesen Ordner verwenden","folderClose":"Schließen","sourceLabelSelect":"Auswahl","categoryChoose":"Alle Kategorien","iconAll":"Alle Quellen","iconProject":"Originalprojekt","aboutLabel":"Install Monitor Informationen","settingsLabel":"Einstellungen","catalogLabel":"App-Store-Quelle","sortLabel":"Katalog-Sortierung","lsioSearchLabel":"LinuxServer.io Images durchsuchen","appSearchLabel":"Apps suchen","sourceRepositoryLabel":"Original-Dokumentation ansehen ↗","licenceLabel":"Logos: selfh.st/icons (CC BY 4.0) ↗","networkNotice":"Nur lokal auf NAS, Änderungen erfordern Neustart.","notAvailable":"Nicht verfügbar","serverUnavailable":"Server nicht erreichbar / server unavailable","serverInvalid":"Ungültige Serverantwort / invalid server response","scanSourceDocumentation":"Docker-Dokumentation","sourceOfficial":"Offizieller LinuxServer.io-Katalog","sourceVerified":"Verifizierte Hersteller-Compose","sourceDetected":"Erkannte Image-/Quellinformationen","sourceMetadata":"Nur OCI-Metadaten: Pflichten und Abhängigkeiten müssen geprüft werden.","sourceConfigCheck":"Konfiguration wird zusätzlich geprüft.","diagnosticUnknown":"Installationsweg nicht erkannt","categoryOthers":"Sonstiges","categoryDeveloper":"Developer","categoryProductivity":"Productivity","categoryMedia":"Media","categoryHome":"Home","categoryNetworking":"Networking","categoryFinance":"Finance","categoryAI":"AI","categorySocial":"Social","stateRunning":"Läuft","stateExited":"Beendet","stateDead":"Fehlgeschlagen","stateCreated":"Erstellt","stateRestarting":"Startet neu","statePaused":"Pausiert","healthHealthy":"Gesund","healthUnhealthy":"Fehlerhaft","healthStarting":"Startet","exitCode":"Exit-Code"},"en":{"sourceImage":"Docker image","sourceUrl":"GitHub / URL","sourceYaml":"Compose YAML","sourceStores":"App catalogs","storesSubtitle":"Choose sources and review apps before installation","mySearch":"Search my apps…","mySearchLabel":"Search personal apps","myRepository":"iSanto1306 Apps – source repository ↗","storeManifest":"ZimaOS store manifest ↗","selfhstNote":"All selfh.st apps are listed. Search filters this directory only. Install Monitor checks prerequisites after selection.","githubNote":"GitHub repositories are fetched after two search characters. Not every repository contains an installable Docker configuration. Sorting applies only to fetched results (maximum 1,000 per query).","iconFolder":"Choose folder","iconPickerTitle":"Choose app icons","iconRescan":"Search again","iconSearch":"Search","iconOrigin":"Icon source","iconSearchLabel":"Search app icons","iconSearchHint":"Search app icon …","iconCatalogLink":"selfh.st directory ↗","targetSystem":"Target system","targetHelp":"ZimaOS is selected by default. Other targets only export a YAML file.","targetZima":"ZimaOS (direct installation)","targetCasa":"CasaOS (export YAML)","targetDocker":"Docker Compose / Portainer (YAML export)","gpuCaution":"Limits apply per container. GPU access is granted only when explicitly selected. The app must support VAAPI, CUDA or NVENC.","timezoneHelp":"Existing TZ values change only if you select a different setting.","proxyTitle":"Authenticator – reverse proxy","proxyHelp":"Enter a current six-digit code before each installation through an HTTPS reverse proxy.","proxyCode":"Authenticator code","buildConsent":"I authorize Install Monitor to build third-party GitHub source code as a Docker image on my NAS. Dockerfile commands can execute code. Privileged containers may gain extended NAS access.","installProgress":"Installation progress","installEvents":"Installation events","aboutCpu":"CPU usage","aboutMemory":"Memory usage","aboutSince":"Online since","aboutVersion":"Version","aboutSupport":"Supported by","aboutDonate":"Support the project","aboutFooter":"Resource usage of the Install Monitor container","aboutUnavailable":"Unavailable","aboutDetected":"Detected","aboutNotDetected":"Not detected","aboutNotChecked":"Not checked","authStatusLoading":"Loading status …","authStart":"Start setup","authScan":"Authenticator → Plus (+) → Other account → Scan QR code.","authManual":"Enter setup key manually instead","setupKey":"Setup key (one-time)","authConfirmCode":"Confirm six-digit code","authEnable":"Enable","authEnabled":"Enabled. Allowed reverse-proxy hosts:","authDisabled":"Not configured. Allowed reverse-proxy hosts:","authNone":"none","authUnset":"none (set IM_ALLOWED_PROXY_HOSTS)","proxyHostsHeading":"Manage reverse-proxy hosts","proxyHostsHelp":"HTTPS endpoints with a valid certificate only. The address must expose the ZimaOS API, not just the Install Monitor page. Changes require authenticator verification.","proxyHostname":"Enter new hostname","proxyChangeCode":"Authenticator code for changes","proxyAdd":"Add host","proxyNoHosts":"No hosts allowed.","proxyRemove":"Remove","proxyCodeRequired":"Enter a six-digit authenticator code.","proxyHostInvalid":"Enter a valid DNS hostname without https://.","proxyHostsUpdated":"Reverse-proxy hosts updated.","installAuthRequired":"Enter authenticator code.","installBuildRequired":"Explicitly approve the local build of third-party GitHub source.","installPreparing":"Preparing installation.","installInterrupted":"Live connection interrupted. Installation may continue on ZimaOS. Check the app status.","scanStartFailed":"GitHub scan could not start.","scanNoSource":"GitHub scan found no Compose source.","scanTimeout":"GitHub scan timed out. Check GitHub API limits and container logs. Nothing was installed.","folderHeading":"Choose NAS folder","folderBack":"Back","folderUse":"Use this folder","folderClose":"Close","sourceLabelSelect":"Selection","categoryChoose":"All categories","iconAll":"All sources","iconProject":"Original project","aboutLabel":"About Install Monitor","settingsLabel":"Settings","catalogLabel":"App directory source","sortLabel":"Directory sorting","lsioSearchLabel":"Search LinuxServer.io images","appSearchLabel":"Search apps","sourceRepositoryLabel":"Open original documentation ↗","licenceLabel":"Icons: selfh.st/icons (CC BY 4.0) ↗","networkNotice":"Local to NAS only; changes require restart.","notAvailable":"Unavailable","serverUnavailable":"Server unavailable","serverInvalid":"Invalid server response","scanSourceDocumentation":"Docker documentation","sourceOfficial":"Official LinuxServer.io catalog","sourceVerified":"Verified publisher Compose","sourceDetected":"Detected image/source details","sourceMetadata":"OCI metadata only: requirements and dependencies must be checked.","sourceConfigCheck":"Configuration will also be checked.","diagnosticUnknown":"Installation method not recognized","categoryOthers":"Other","categoryDeveloper":"Development","categoryProductivity":"Productivity","categoryMedia":"Media","categoryHome":"Home","categoryNetworking":"Networking","categoryFinance":"Finance","categoryAI":"AI","categorySocial":"Social","stateRunning":"Running","stateExited":"Exited","stateDead":"Dead","stateCreated":"Created","stateRestarting":"Restarting","statePaused":"Paused","healthHealthy":"Healthy","healthUnhealthy":"Unhealthy","healthStarting":"Starting","exitCode":"Exit code"},"fr":{"sourceImage":"Image Docker","sourceUrl":"GitHub / URL","sourceYaml":"Compose YAML","sourceStores":"Catalogues d’apps","storesSubtitle":"Choisissez les sources et vérifiez les apps avant installation","mySearch":"Rechercher mes apps…","mySearchLabel":"Rechercher mes apps","myRepository":"iSanto1306 Apps – dépôt source ↗","storeManifest":"Manifeste de la boutique ZimaOS ↗","selfhstNote":"Toutes les apps selfh.st sont affichées. La recherche filtre uniquement ce catalogue. Install Monitor vérifie les prérequis après sélection.","githubNote":"Les dépôts GitHub sont recherchés à partir de deux caractères. Tous ne contiennent pas une configuration Docker installable. Le tri ne concerne que les résultats chargés (1 000 maximum par recherche).","iconFolder":"Choisir un dossier","iconPickerTitle":"Choisir des logos d’app","iconRescan":"Rechercher","iconSearch":"Rechercher","iconOrigin":"Source du logo","iconSearchLabel":"Rechercher un logo d’app","iconSearchHint":"Rechercher un logo …","iconCatalogLink":"Catalogue selfh.st ↗","targetSystem":"Système cible","targetHelp":"ZimaOS est sélectionné par défaut. Les autres systèmes exportent uniquement un fichier YAML.","targetZima":"ZimaOS (installation directe)","targetCasa":"CasaOS (export YAML)","targetDocker":"Docker Compose / Portainer (export YAML)","gpuCaution":"Les limites sont appliquées par conteneur. L’accès GPU nécessite une sélection explicite. L’application doit prendre en charge VAAPI, CUDA ou NVENC.","timezoneHelp":"Les valeurs TZ existantes ne changent que si vous sélectionnez une autre option.","proxyTitle":"Authentificateur – proxy inverse","proxyHelp":"Saisissez un code à six chiffres valide avant chaque installation via un proxy inverse HTTPS.","proxyCode":"Code d’authentification","buildConsent":"J’autorise Install Monitor à compiler du code source GitHub tiers en image Docker sur mon NAS. Les commandes Dockerfile peuvent exécuter du code. Les conteneurs privilégiés peuvent bénéficier d’un accès étendu au NAS.","installProgress":"Progression de l’installation","installEvents":"Journal des étapes d’installation","aboutCpu":"Utilisation CPU","aboutMemory":"Mémoire utilisée","aboutSince":"En ligne depuis","aboutVersion":"Version","aboutSupport":"Développé par","aboutDonate":"Soutenir le projet","aboutFooter":"Utilisation des ressources du conteneur Install Monitor","aboutUnavailable":"Indisponible","aboutDetected":"Détecté","aboutNotDetected":"Non détecté","aboutNotChecked":"Non vérifié","authStatusLoading":"Chargement de l’état …","authStart":"Démarrer la configuration","authScan":"Authentificateur → Plus (+) → Autre compte → Scanner le code QR.","authManual":"Saisir plutôt la clé manuellement","setupKey":"Clé de configuration (usage unique)","authConfirmCode":"Confirmer le code à six chiffres","authEnable":"Activer","authEnabled":"Activé. Hôtes proxy inverse autorisés :","authDisabled":"Non configuré. Hôtes proxy inverse autorisés :","authNone":"aucun","authUnset":"aucun (définir IM_ALLOWED_PROXY_HOSTS)","proxyHostsHeading":"Gérer les hôtes proxy inverse","proxyHostsHelp":"Uniquement des adresses HTTPS avec un certificat valide. L’adresse doit exposer l’API ZimaOS, pas seulement Install Monitor. Les modifications nécessitent une authentification.","proxyHostname":"Saisir un nouveau nom d’hôte","proxyChangeCode":"Code d’authentification pour modifier","proxyAdd":"Ajouter un hôte","proxyNoHosts":"Aucun hôte autorisé.","proxyRemove":"Supprimer","proxyCodeRequired":"Saisissez un code d’authentification à six chiffres.","proxyHostInvalid":"Saisissez un nom d’hôte DNS valide sans https://.","proxyHostsUpdated":"Hôtes proxy inverse mis à jour.","installAuthRequired":"Saisissez le code d’authentification.","installBuildRequired":"Confirmez expressément la compilation locale de sources GitHub tierces.","installPreparing":"Préparation de l’installation.","installInterrupted":"Connexion en direct interrompue. L’installation peut continuer sur ZimaOS. Vérifiez l’état de l’app.","scanStartFailed":"Impossible de démarrer l’analyse GitHub.","scanNoSource":"L’analyse GitHub n’a trouvé aucune source Compose.","scanTimeout":"L’analyse GitHub a expiré. Vérifiez les limites API GitHub et les journaux du conteneur. Rien n’a été installé.","folderHeading":"Choisir un dossier du NAS","folderBack":"Retour","folderUse":"Utiliser ce dossier","folderClose":"Fermer","sourceLabelSelect":"Sélection","categoryChoose":"Toutes les catégories","iconAll":"Toutes les sources","iconProject":"Projet original","aboutLabel":"Informations sur Install Monitor","settingsLabel":"Paramètres","catalogLabel":"Source du catalogue","sortLabel":"Tri du catalogue","lsioSearchLabel":"Rechercher les images LinuxServer.io","appSearchLabel":"Rechercher des apps","sourceRepositoryLabel":"Ouvrir la documentation originale ↗","licenceLabel":"Logos : selfh.st/icons (CC BY 4.0) ↗","networkNotice":"NAS local uniquement ; les modifications nécessitent un redémarrage.","notAvailable":"Indisponible","serverUnavailable":"Serveur inaccessible","serverInvalid":"Réponse serveur invalide","scanSourceDocumentation":"Documentation Docker","sourceOfficial":"Catalogue officiel LinuxServer.io","sourceVerified":"Compose vérifié de l’éditeur","sourceDetected":"Informations détectées sur l’image/source","sourceMetadata":"Métadonnées OCI uniquement : vérifiez les prérequis et dépendances.","sourceConfigCheck":"La configuration sera également vérifiée.","diagnosticUnknown":"Méthode d’installation non reconnue","categoryOthers":"Autres","categoryDeveloper":"Développement","categoryProductivity":"Productivité","categoryMedia":"Médias","categoryHome":"Domotique","categoryNetworking":"Réseau","categoryFinance":"Finance","categoryAI":"IA","categorySocial":"Réseaux sociaux","stateRunning":"En cours","stateExited":"Arrêté","stateDead":"Échec","stateCreated":"Créé","stateRestarting":"Redémarrage","statePaused":"En pause","healthHealthy":"Sain","healthUnhealthy":"Défaillant","healthStarting":"Démarrage","exitCode":"Code de sortie"},"pt":{"sourceImage":"Imagem Docker","sourceUrl":"GitHub / URL","sourceYaml":"Compose YAML","sourceStores":"Catálogos de apps","storesSubtitle":"Escolha as fontes e verifique as apps antes de instalar","mySearch":"Pesquisar as minhas apps…","mySearchLabel":"Pesquisar apps próprias","myRepository":"iSanto1306 Apps – repositório de origem ↗","storeManifest":"Manifesto da loja ZimaOS ↗","selfhstNote":"Todas as apps selfh.st são apresentadas. A pesquisa filtra apenas este catálogo. O Install Monitor verifica os requisitos após a seleção.","githubNote":"Os repositórios GitHub são pesquisados a partir de dois caracteres. Nem todos contêm uma configuração Docker instalável. A ordenação aplica-se apenas aos resultados carregados (máximo de 1 000 por pesquisa).","iconFolder":"Escolher pasta","iconPickerTitle":"Escolher logótipos de apps","iconRescan":"Pesquisar novamente","iconSearch":"Pesquisar","iconOrigin":"Origem do logótipo","iconSearchLabel":"Pesquisar logótipo de app","iconSearchHint":"Pesquisar logótipo …","iconCatalogLink":"Catálogo selfh.st ↗","targetSystem":"Sistema de destino","targetHelp":"ZimaOS está selecionado por predefinição. Outros sistemas exportam apenas o ficheiro YAML.","targetZima":"ZimaOS (instalação direta)","targetCasa":"CasaOS (exportar YAML)","targetDocker":"Docker Compose / Portainer (exportar YAML)","gpuCaution":"Os limites aplicam-se por contentor. O acesso à GPU requer seleção explícita. A app deve suportar VAAPI, CUDA ou NVENC.","timezoneHelp":"Os valores TZ existentes só mudam se escolher outra opção.","proxyTitle":"Autenticador – proxy inverso","proxyHelp":"Introduza um código atual de seis dígitos antes de instalar através de um proxy inverso HTTPS.","proxyCode":"Código do autenticador","buildConsent":"Autorizo o Install Monitor a compilar código de terceiros do GitHub como imagem Docker no meu NAS. Os comandos Dockerfile podem executar código. Contentores privilegiados podem obter acesso alargado ao NAS.","installProgress":"Progresso da instalação","installEvents":"Registo dos passos de instalação","aboutCpu":"Utilização da CPU","aboutMemory":"Utilização de memória","aboutSince":"Online desde","aboutVersion":"Versão","aboutSupport":"Desenvolvido por","aboutDonate":"Apoiar o projeto","aboutFooter":"Utilização de recursos do contentor Install Monitor","aboutUnavailable":"Indisponível","aboutDetected":"Detetado","aboutNotDetected":"Não detetado","aboutNotChecked":"Não verificado","authStatusLoading":"A carregar estado …","authStart":"Iniciar configuração","authScan":"Autenticador → Mais (+) → Outra conta → Ler código QR.","authManual":"Em alternativa, introduzir chave manualmente","setupKey":"Chave de configuração (utilização única)","authConfirmCode":"Confirmar código de seis dígitos","authEnable":"Ativar","authEnabled":"Ativado. Hosts de proxy inverso permitidos:","authDisabled":"Ainda não configurado. Hosts de proxy inverso permitidos:","authNone":"nenhum","authUnset":"nenhum (definir IM_ALLOWED_PROXY_HOSTS)","proxyHostsHeading":"Gerir hosts de proxy inverso","proxyHostsHelp":"Apenas destinos HTTPS com certificado válido. O endereço tem de disponibilizar a API do ZimaOS, não apenas a página do Install Monitor. As alterações requerem autenticação.","proxyHostname":"Introduzir novo nome de host","proxyChangeCode":"Código do autenticador para alterações","proxyAdd":"Adicionar host","proxyNoHosts":"Nenhum host autorizado.","proxyRemove":"Remover","proxyCodeRequired":"Introduza um código de autenticador de seis dígitos.","proxyHostInvalid":"Introduza um nome de host DNS válido sem https://.","proxyHostsUpdated":"Hosts de proxy inverso atualizados.","installAuthRequired":"Introduza o código do autenticador.","installBuildRequired":"Confirme expressamente a compilação local de código de terceiros do GitHub.","installPreparing":"A preparar a instalação.","installInterrupted":"Ligação em direto interrompida. A instalação pode continuar no ZimaOS. Verifique o estado da app.","scanStartFailed":"Não foi possível iniciar a análise do GitHub.","scanNoSource":"A análise do GitHub não encontrou ficheiro Compose.","scanTimeout":"A análise do GitHub demorou demasiado. Verifique os limites da API e os registos do contentor. Nada foi instalado.","folderHeading":"Escolher pasta do NAS","folderBack":"Voltar","folderUse":"Usar esta pasta","folderClose":"Fechar","sourceLabelSelect":"Seleção","categoryChoose":"Todas as categorias","iconAll":"Todas as fontes","iconProject":"Projeto original","aboutLabel":"Informações do Install Monitor","settingsLabel":"Definições","catalogLabel":"Origem do catálogo","sortLabel":"Ordenação do catálogo","lsioSearchLabel":"Pesquisar imagens LinuxServer.io","appSearchLabel":"Pesquisar apps","sourceRepositoryLabel":"Abrir documentação original ↗","licenceLabel":"Logótipos: selfh.st/icons (CC BY 4.0) ↗","networkNotice":"Apenas local no NAS; as alterações exigem reinício.","notAvailable":"Indisponível","serverUnavailable":"Servidor indisponível","serverInvalid":"Resposta do servidor inválida","scanSourceDocumentation":"Documentação Docker","sourceOfficial":"Catálogo oficial LinuxServer.io","sourceVerified":"Compose verificado do fabricante","sourceDetected":"Informação detetada da imagem/fonte","sourceMetadata":"Apenas metadados OCI: verifique requisitos e dependências.","sourceConfigCheck":"A configuração também será verificada.","diagnosticUnknown":"Método de instalação não reconhecido","categoryOthers":"Outros","categoryDeveloper":"Desenvolvimento","categoryProductivity":"Produtividade","categoryMedia":"Multimédia","categoryHome":"Casa","categoryNetworking":"Rede","categoryFinance":"Finanças","categoryAI":"IA","categorySocial":"Social","stateRunning":"Em execução","stateExited":"Terminado","stateDead":"Falhou","stateCreated":"Criado","stateRestarting":"A reiniciar","statePaused":"Em pausa","healthHealthy":"Saudável","healthUnhealthy":"Com problemas","healthStarting":"A iniciar","exitCode":"Código de saída"},"es":{"sourceImage":"Imagen Docker","sourceUrl":"GitHub / URL","sourceYaml":"Compose YAML","sourceStores":"Catálogos de apps","storesSubtitle":"Selecciona fuentes y comprueba las apps antes de instalar","mySearch":"Buscar mis apps…","mySearchLabel":"Buscar mis apps","myRepository":"iSanto1306 Apps – repositorio de origen ↗","storeManifest":"Manifiesto de la tienda ZimaOS ↗","selfhstNote":"Se muestran todas las apps de selfh.st. La búsqueda filtra solo este catálogo. Install Monitor comprueba los requisitos tras seleccionar una app.","githubNote":"Los repositorios GitHub se buscan a partir de dos caracteres. No todos contienen una configuración Docker instalable. La ordenación solo afecta a los resultados cargados (máximo 1.000 por búsqueda).","iconFolder":"Elegir carpeta","iconPickerTitle":"Elegir logos de apps","iconRescan":"Buscar de nuevo","iconSearch":"Buscar","iconOrigin":"Origen del logo","iconSearchLabel":"Buscar logo de app","iconSearchHint":"Buscar logo …","iconCatalogLink":"Catálogo selfh.st ↗","targetSystem":"Sistema de destino","targetHelp":"ZimaOS está seleccionado por defecto. Los demás sistemas solo exportan el archivo YAML.","targetZima":"ZimaOS (instalación directa)","targetCasa":"CasaOS (exportar YAML)","targetDocker":"Docker Compose / Portainer (exportar YAML)","gpuCaution":"Los límites se aplican por contenedor. El acceso a la GPU requiere selección explícita. La app debe admitir VAAPI, CUDA o NVENC.","timezoneHelp":"Los valores TZ existentes solo cambian si eliges otra opción.","proxyTitle":"Autenticador – proxy inverso","proxyHelp":"Introduce un código actual de seis dígitos antes de instalar mediante un proxy inverso HTTPS.","proxyCode":"Código del autenticador","buildConsent":"Autorizo a Install Monitor a compilar código de terceros de GitHub como imagen Docker en mi NAS. Las instrucciones Dockerfile pueden ejecutar código. Los contenedores privilegiados pueden obtener acceso ampliado al NAS.","installProgress":"Progreso de instalación","installEvents":"Registro de los pasos de instalación","aboutCpu":"Uso de CPU","aboutMemory":"Uso de memoria","aboutSince":"En línea desde","aboutVersion":"Versión","aboutSupport":"Desarrollado por","aboutDonate":"Apoyar el proyecto","aboutFooter":"Uso de recursos del contenedor Install Monitor","aboutUnavailable":"No disponible","aboutDetected":"Detectado","aboutNotDetected":"No detectado","aboutNotChecked":"No comprobado","authStatusLoading":"Cargando estado …","authStart":"Iniciar configuración","authScan":"Autenticador → Más (+) → Otra cuenta → Escanear código QR.","authManual":"Introducir la clave manualmente","setupKey":"Clave de configuración (un solo uso)","authConfirmCode":"Confirmar código de seis dígitos","authEnable":"Activar","authEnabled":"Activado. Hosts de proxy inverso permitidos:","authDisabled":"Sin configurar. Hosts de proxy inverso permitidos:","authNone":"ninguno","authUnset":"ninguno (configurar IM_ALLOWED_PROXY_HOSTS)","proxyHostsHeading":"Administrar hosts de proxy inverso","proxyHostsHelp":"Solo destinos HTTPS con certificado válido. La dirección debe ofrecer la API de ZimaOS, no solo la página de Install Monitor. Los cambios requieren autenticación.","proxyHostname":"Introducir nuevo nombre de host","proxyChangeCode":"Código del autenticador para cambios","proxyAdd":"Añadir host","proxyNoHosts":"No hay hosts permitidos.","proxyRemove":"Eliminar","proxyCodeRequired":"Introduce un código de autenticador de seis dígitos.","proxyHostInvalid":"Introduce un nombre de host DNS válido sin https://.","proxyHostsUpdated":"Hosts de proxy inverso actualizados.","installAuthRequired":"Introduce el código del autenticador.","installBuildRequired":"Confirma expresamente la compilación local de código de terceros de GitHub.","installPreparing":"Preparando la instalación.","installInterrupted":"Conexión en directo interrumpida. La instalación puede continuar en ZimaOS. Comprueba el estado de la app.","scanStartFailed":"No se pudo iniciar el análisis de GitHub.","scanNoSource":"El análisis de GitHub no encontró ningún archivo Compose.","scanTimeout":"La búsqueda GitHub tardó demasiado. Comprueba los límites de API y los registros del contenedor. No se instaló nada.","folderHeading":"Elegir carpeta del NAS","folderBack":"Atrás","folderUse":"Usar esta carpeta","folderClose":"Cerrar","sourceLabelSelect":"Selección","categoryChoose":"Todas las categorías","iconAll":"Todas las fuentes","iconProject":"Proyecto original","aboutLabel":"Información sobre Install Monitor","settingsLabel":"Configuración","catalogLabel":"Origen del catálogo","sortLabel":"Ordenación del catálogo","lsioSearchLabel":"Buscar imágenes LinuxServer.io","appSearchLabel":"Buscar apps","sourceRepositoryLabel":"Abrir documentación original ↗","licenceLabel":"Logos: selfh.st/icons (CC BY 4.0) ↗","networkNotice":"Solo local en el NAS; los cambios requieren reiniciar.","notAvailable":"No disponible","serverUnavailable":"Servidor no disponible","serverInvalid":"Respuesta del servidor no válida","scanSourceDocumentation":"Documentación Docker","sourceOfficial":"Catálogo oficial LinuxServer.io","sourceVerified":"Compose verificado del fabricante","sourceDetected":"Información detectada de imagen/origen","sourceMetadata":"Solo metadatos OCI: comprueba requisitos y dependencias.","sourceConfigCheck":"También se comprobará la configuración.","diagnosticUnknown":"Método de instalación no reconocido","categoryOthers":"Otros","categoryDeveloper":"Desarrollo","categoryProductivity":"Productividad","categoryMedia":"Multimedia","categoryHome":"Hogar","categoryNetworking":"Redes","categoryFinance":"Finanzas","categoryAI":"IA","categorySocial":"Social","stateRunning":"En ejecución","stateExited":"Finalizado","stateDead":"Fallido","stateCreated":"Creado","stateRestarting":"Reiniciando","statePaused":"En pausa","healthHealthy":"Saludable","healthUnhealthy":"Con problemas","healthStarting":"Iniciando","exitCode":"Código de salida"}};
// Explain the different URLs without exposing private NAS addresses in the store.
const zimaAddressGuidance={
 de:{hostHelp:'Hier gehört die Adresse deiner ZimaOS-Verwaltungsoberfläche hinein (z. B. http://NAS-LAN-IP), nicht die Install-Monitor-Domain.',internalTitle:'Interne ZimaOS-Adresse (bei Reverse Proxy)',internalHelp:'Nur wenn du oben die öffentliche ZimaOS-Reverse-Proxy-Domain angibst: hier die LAN-IP der ZimaOS-Oberfläche eintragen. Auch ohne IM_INTERNAL_ZIMAOS_URL möglich.',internalPlaceholder:'http://NAS-LAN-IP'},
 en:{hostHelp:'Enter the address of your ZimaOS administration page (e.g. http://NAS-LAN-IP), not the Install Monitor domain.',internalTitle:'Internal ZimaOS address (reverse proxy)',internalHelp:'Only when using a public ZimaOS proxy hostname above: enter the ZimaOS LAN IP here. No IM_INTERNAL_ZIMAOS_URL environment variable is needed.',internalPlaceholder:'http://NAS-LAN-IP'},
 fr:{hostHelp:'Indiquez l’adresse de l’interface ZimaOS (p. ex. http://NAS-LAN-IP), pas le domaine Install Monitor.',internalTitle:'Adresse ZimaOS interne (proxy inverse)',internalHelp:'Si vous utilisez un domaine proxy public ci-dessus, saisissez ici l’IP locale de ZimaOS. La variable IM_INTERNAL_ZIMAOS_URL est facultative.',internalPlaceholder:'http://NAS-LAN-IP'},
 pt:{hostHelp:'Introduza o endereço da administração do ZimaOS (por exemplo http://NAS-LAN-IP), não o domínio do Install Monitor.',internalTitle:'Endereço interno do ZimaOS (proxy inverso)',internalHelp:'Se usar o domínio público de proxy do ZimaOS acima, introduza aqui o IP da rede local. IM_INTERNAL_ZIMAOS_URL é opcional.',internalPlaceholder:'http://NAS-LAN-IP'},
 es:{hostHelp:'Indica la dirección de administración de ZimaOS (p. ej. http://NAS-LAN-IP), no el dominio de Install Monitor.',internalTitle:'Dirección interna de ZimaOS (proxy inverso)',internalHelp:'Si utilizas arriba un dominio público del proxy ZimaOS, escribe aquí la IP local. No es necesaria la variable IM_INTERNAL_ZIMAOS_URL.',internalPlaceholder:'http://NAS-LAN-IP'}
};
for(const [code,values] of Object.entries(zimaAddressGuidance))Object.assign(imExtraTexts[code],values);
const imProxySecurityGuidance={"de":{"proxyHelp":"Bei aktiviertem Authenticator oder freigegebenem Reverse Proxy ist für jede Installation ein sechsstelliger Code nötig, auch im LAN.","proxyHostsHelp":"Öffentliche HTTPS-Domain des Install Monitor eintragen, nicht die NAS-IP. Sobald ein Proxy-Host freigegeben ist, benötigen alle Installationen den Authenticator-Code.","hostHelp":"ZimaOS-Verwaltungsadresse (z. B. http://NAS-LAN-IP), nicht die Install-Monitor-Domain. Wird auf dem NAS gespeichert; Benutzername und Passwort nicht."},"en":{"proxyHelp":"When an authenticator is enabled or reverse proxy access is allowed, every installation requires a six-digit code, including on the LAN.","proxyHostsHelp":"Enter the public HTTPS hostname of Install Monitor, not the NAS IP. Once a proxy hostname is allowed, every installation requires an authenticator code.","hostHelp":"ZimaOS administration URL (e.g. http://NAS-LAN-IP), not the Install Monitor domain. Saved on the NAS; username and password are not saved."},"fr":{"proxyHelp":"Avec un authentificateur actif ou un proxy inverse autorisé, chaque installation exige un code à six chiffres, même en local.","proxyHostsHelp":"Saisissez le domaine HTTPS public d’Install Monitor, pas l’IP du NAS. Chaque installation nécessitera le code de l’authentificateur.","hostHelp":"Adresse d’administration ZimaOS (ex. http://NAS-LAN-IP), pas le domaine Install Monitor. Enregistrée sur le NAS ; identifiants non enregistrés."},"pt":{"proxyHelp":"Com o autenticador ativo ou um proxy inverso autorizado, cada instalação exige um código de seis dígitos, mesmo na rede local.","proxyHostsHelp":"Introduza o domínio HTTPS público do Install Monitor, não o IP do NAS. Cada instalação exigirá o código do autenticador.","hostHelp":"Endereço de administração do ZimaOS (por ex. http://NAS-LAN-IP), não o domínio Install Monitor. Guardado no NAS; utilizador e palavra-passe não são guardados."},"es":{"proxyHelp":"Con el autenticador activo o un proxy inverso autorizado, cada instalación exige un código de seis dígitos, incluso en la red local.","proxyHostsHelp":"Introduce el dominio HTTPS público de Install Monitor, no la IP del NAS. Cada instalación requerirá el código del autenticador.","hostHelp":"Dirección de administración ZimaOS (p. ej. http://NAS-LAN-IP), no el dominio Install Monitor. Se guarda en el NAS; el usuario y la contraseña no."}};
for(const [code,values] of Object.entries(imProxySecurityGuidance))Object.assign(imExtraTexts[code],values);
const ux=key=>imExtraTexts[lang]?.[key]??imExtraTexts.de[key]??key;
function translateAdditionalUI(){
 $$('[data-ui]').forEach(el=>{
  const value=ux(el.dataset.ui);let found=false;
  // Never use textContent on provider buttons: keep their logo images intact.
  for(const node of el.childNodes){if(node.nodeType===Node.TEXT_NODE&&node.textContent.trim()){
   if(!found){node.textContent=value;found=true}else node.textContent='';
  }}
  if(!found)el.append(document.createTextNode(value));
 });
 $$('[data-ui-placeholder]').forEach(el=>el.placeholder=ux(el.dataset.uiPlaceholder));
 $$('[data-ui-aria]').forEach(el=>el.setAttribute('aria-label',ux(el.dataset.uiAria)));
 $$('[data-ui-title]').forEach(el=>el.title=ux(el.dataset.uiTitle));
}

function translate(){document.documentElement.lang=lang;$$('[data-t]').forEach(el=>el.textContent=t(el.dataset.t));$$('[data-p]').forEach(el=>el.placeholder=t(el.dataset.p));$('#language').value=lang;const current=$('#imLanguageCurrent');if(current)current.textContent=$('#language').selectedOptions[0]?.textContent||'Deutsch';$$('#imLanguageMenu [data-lang]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.lang===lang)));setSourceType(kind);updateInstallAction();translateAdditionalUI();}
function notice(msg,error=false){const el=$('#notification');el.textContent=msg;el.classList.toggle('error',error);el.hidden=!msg;}
function errorMessage(e){return e.message||t('invalid');}
const diagnosisLabels={
 de:{evidence:'Erkannt anhand',action:'Empfohlener Weg',docs:'Original-Dokumentation ansehen ↗',limited:'Hinweis: Der Repository-Scan war begrenzt. Das Ergebnis ist keine vollständige Aussage über alle Dateien.'},
 en:{evidence:'Evidence',action:'Recommended approach',docs:'Open original documentation ↗',limited:'The repository scan was limited. Not every file could be inspected.'},
 fr:{evidence:'Éléments détectés',action:'Méthode recommandée',docs:'Voir la documentation d’origine ↗',limited:'L’analyse du dépôt était limitée; tous les fichiers n’ont pas été examinés.'},
 pt:{evidence:'Identificado a partir de',action:'Método recomendado',docs:'Consultar documentação original ↗',limited:'A análise do repositório foi limitada; nem todos os ficheiros foram verificados.'},
 es:{evidence:'Detectado a partir de',action:'Método recomendado',docs:'Ver documentación original ↗',limited:'El análisis del repositorio fue limitado; no se revisaron todos los archivos.'}
};
let currentSourceDiagnosis=null;
function showSourceDiagnosis(data){
 const panel=$('#sourceDiagnosis');currentSourceDiagnosis=data&&data.code==='unsupported_source'?data:null;
 panel.hidden=!currentSourceDiagnosis;if(!currentSourceDiagnosis)return;
 const tr=diagnosisLabels[lang]||diagnosisLabels.de;
 $('#sourceDiagnosisTitle').textContent=data.title||ux('diagnosticUnknown');
 $('#sourceDiagnosisReason').textContent=data.explanation||data.message||'';
 $('#sourceDiagnosisEvidenceTitle').textContent=tr.evidence;
 const list=$('#sourceDiagnosisEvidence');list.replaceChildren();
 const evidence=Array.isArray(data.evidence)?data.evidence:[];
 for(const entry of evidence.slice(0,5)){const li=document.createElement('li');li.textContent=String(entry);list.appendChild(li)}
 $('#sourceDiagnosisEvidenceTitle').hidden=list.hidden=!evidence.length;
 $('#sourceDiagnosisActionTitle').textContent=tr.action;
 $('#sourceDiagnosisRecommendation').textContent=data.recommendation||'';
 const command=$('#sourceDiagnosisCommand');command.textContent=data.command||'';command.hidden=!data.command;
 const limited=$('#sourceDiagnosisLimited');limited.hidden=!data.scan_limited;limited.textContent=tr.limited;
 const link=$('#sourceDiagnosisLink');const url=String(data.documentation_url||'');
 // Only link to canonical GitHub docs, never execute instructions found in a README.
 if(/^https:\/\/github\.com\/[a-zA-Z0-9-]+\/[a-zA-Z0-9_.-]+(?:\/|$)/.test(url)){
  link.hidden=false;link.href=url;link.textContent=tr.docs;
 }else{link.hidden=true;link.removeAttribute('href')}
}
async function request(path,body,authenticated=true){const opts={credentials:'same-origin',headers:{'Accept':'application/json'}};if(body!==undefined){opts.method='POST';opts.headers['Content-Type']='application/json';if(authenticated)opts.headers['X-IM-CSRF']=csrf;opts.body=JSON.stringify(body)}let response;try{response=await fetch(path,opts)}catch(e){throw Error(ux('serverUnavailable'))}let data;try{data=await response.json()}catch(e){throw Error(ux('serverInvalid'))}if(!response.ok){if(response.status===401&&authenticated&&path!='/api/login')showLogin();const error=Error(typeof data.detail==='string'?data.detail:(data.detail?.message||JSON.stringify(data.detail||data)));if(data.detail?.code==='unsupported_source')error.diagnostic=data.detail;throw error}return data}
function showLogin(){$('#app').hidden=true;$('#loginScreen').classList.remove('hidden');$('#loginScreen').hidden=false;csrf='';}
function showApp(){$('#app').hidden=false;$('#loginScreen').hidden=true;$('#loginScreen').classList.add('hidden');void loadZimaOsTarget();void setupAuthenticatorStatus();}
/* v0.2.48: separate resize grip from the 6px editor scrollbar.
   Applies ONLY to the three Compose/YAML textareas, including the source tab
   textarea recreated when switching from Docker Image / URL. */
function imCodeEditorGrips(){
 const labels={
  de:'Compose-Feld höher oder niedriger ziehen; Pfeiltasten zum Ändern der Höhe',
  en:'Drag to resize Compose editor; use arrow keys to change height',
  fr:'Redimensionner l’éditeur Compose ; flèches pour régler la hauteur',
  pt:'Arrastar para redimensionar o editor Compose; setas para ajustar a altura',
  es:'Arrastrar para cambiar el tamaño del editor Compose; flechas para ajustar la altura'
 };
 document.querySelectorAll('textarea.code-editor').forEach(area=>{
  if(area.parentElement?.classList.contains('im-code-editor-frame')){
   const grip=area.parentElement.querySelector('.im-code-editor-resizer');
   if(grip){grip.setAttribute('aria-label',labels[lang]||labels.de);grip.title=grip.getAttribute('aria-label');}
   return;
  }
  const frame=document.createElement('div');frame.className='im-code-editor-frame';
  area.before(frame);frame.appendChild(area);
  const grip=document.createElement('button');grip.type='button';
  grip.className='im-code-editor-resizer';grip.setAttribute('aria-label',labels[lang]||labels.de);
  grip.title=grip.getAttribute('aria-label');
  grip.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="2"><path d="M5 19 19 5M11 19l8-8M17 19l2-2"/></svg>';
  const height=()=>area.getBoundingClientRect().height;
  const setHeight=h=>{area.style.height=Math.max(130,Math.round(h))+'px';};
  grip.addEventListener('pointerdown',ev=>{
   if(ev.button!==0)return;
   ev.preventDefault();const y=ev.clientY;const h=height();const id=ev.pointerId;
   grip.setPointerCapture(id);
   const onMove=e=>{if(e.pointerId===id)setHeight(h+e.clientY-y);};
   const onEnd=e=>{if(e.pointerId!==id)return;grip.removeEventListener('pointermove',onMove);grip.removeEventListener('pointerup',onEnd);grip.removeEventListener('pointercancel',onEnd);};
   grip.addEventListener('pointermove',onMove);grip.addEventListener('pointerup',onEnd);grip.addEventListener('pointercancel',onEnd);
  });
  grip.addEventListener('keydown',e=>{
   if(e.key!=='ArrowDown'&&e.key!=='ArrowUp')return;
   e.preventDefault();setHeight(height()+(e.key==='ArrowDown'?32:-32));
  });
  frame.append(grip);
 });
}
function setSourceType(next){
 kind=next;
 $$('.source-tab').forEach(btn=>btn.classList.toggle('active',btn.dataset.kind===kind));
 $('#imageOptions').hidden=kind!=='image';
 const isStores=kind==='stores';
 const isLsio=kind==='lsio'||(isStores&&imStoreProvider==='linuxserver');
 const isApps=kind==='selfhst-apps'||(isStores&&(imStoreProvider==='selfhst'||imStoreProvider==='github'));
 const isMine=isStores&&imStoreProvider==='mine';
 $('#imStoresBrowser').hidden=!isStores;
 $('#imStoresMine').hidden=!isMine;
 $('#lsioBrowser').hidden=!isLsio;
 $('#selfhstAppsBrowser').hidden=!isApps;
 $('#imStoresLsioAnalyze').hidden=!(isStores&&isLsio);
 $('#imStoresLsioAnalyze').disabled=!lsioSelected;
 $('#sourceLabel').hidden=isLsio||isApps||isStores;
 $('#sourceInput').hidden=isLsio||isApps||isStores;
 $('#sourceLabel').textContent=isLsio?'LinuxServer.io':t(kind+'Input');
 $('#sourceHint').textContent=isStores?'':isApps?sl('source'):isLsio?lw('hint'):t(kind+'Hint');
 const el=$('#sourceInput');
 if(kind!=='yaml' && el.tagName==='TEXTAREA' && el.parentElement?.classList.contains('im-code-editor-frame')){
  el.parentElement.replaceWith(el);
 }
 el.placeholder=kind==='image'?'ghcr.io/owner/app:latest':kind==='url'?'https://github.com/owner/repo/blob/main/docker-compose.yml':'name: my-app\nservices:\n  my-app:\n    image: nginx:alpine';
 if(kind==='yaml'){
  if(el.tagName!=='TEXTAREA')el.outerHTML='<textarea id="sourceInput" class="code-editor" rows="9" spellcheck="false" placeholder="name: my-app&#10;services:&#10;  my-app:&#10;    image: nginx:alpine"></textarea>';
 }else if(el.tagName==='TEXTAREA'){
  el.outerHTML='<input id="sourceInput" autocomplete="off" spellcheck="false">';
  $('#sourceInput').placeholder=kind==='image'?'ghcr.io/owner/app:latest':'https://github.com/owner/repo/blob/main/docker-compose.yml';
 }
 $('#sourceInput').hidden=isLsio||isApps||isStores;imCodeEditorGrips();selfhstAppsTranslate();imStoresTranslate();
 $('#analyzeBtn').hidden=isApps||isStores;
 if(isApps){selfhstAppsTranslate();if(imStoreProvider==='selfhst')loadSelfhstApps();else renderSelfhstApps();}
 if(isMine)void imLoadMyStore();
 if(isLsio){$('#lsioSearch').placeholder=lw('search');const any=$('#lsioCategory option[value=""]');if(any)any.textContent=lw('all');loadLsio();}
}

// Protect Install Monitor's single-page wizard from accidental browser/mouse Back.
// Internal wizard buttons still use selectStep(); they do not use browser history.
function installBrowserBackGuard(){
  if(!window.history?.pushState || !window.history?.replaceState)return;
  const key='__installMonitorBrowserBackGuard';
  let enabled=false;
  const mark=kind=>({[key]:kind});
  const isGuard=()=>window.history.state?.[key]==='guard';
  const pushGuard=()=>window.history.pushState(mark('guard'),'',window.location.href);
  try{
    // A real same-document entry remains behind the guard, preventing a Back
    // press from immediately navigating to the site visited before this one.
    if(!isGuard()){
      window.history.replaceState(mark('base'),'',window.location.href);
      pushGuard();
    }
    enabled=true;
  }catch(_){return;}
  window.addEventListener('popstate',()=>{
    if(!enabled || isGuard())return;
    try{pushGuard();}catch(_){}
  });
  // Chromium can skip programmatic history entries made without a user gesture.
  // Re-arm once on the first real interaction, not on every click/back press.
  let refreshed=false;
  const refresh=event=>{
    if(refreshed || !event.isTrusted)return;
    refreshed=true;
    document.removeEventListener('pointerdown',refresh,true);
    document.removeEventListener('keydown',refresh,true);
    try{
      window.history.replaceState(mark('base'),'',window.location.href);
      pushGuard();
    }catch(_){}
  };
  document.addEventListener('pointerdown',refresh,true);
  document.addEventListener('keydown',refresh,true);
  // Browser-side mouse Back/Forward is not always a cancellable DOM action;
  // this is best effort, whereas popstate/history provide the primary guard.
  document.addEventListener('auxclick',event=>{
    if(event.button===3 || event.button===4)event.preventDefault();
  },true);
}

function selectStep(number){step=number;const ids=['sourcePanel','configPanel','previewPanel','executePanel'];ids.forEach((id,index)=>$('#'+id).classList.toggle('hidden',index!==step-1));for(let i=1;i<=4;i++){const el=$('#step'+i);el.classList.toggle('active',i===number);el.classList.toggle('done',i<number)}notice('');}
function setBusy(value,button){busy=value;$$('.primary,.secondary').forEach(el=>el.disabled=value);$('#proceedBtn').disabled=value||!planReady;if(button)button.disabled=value;updateInstallAction();}
async function refreshPortScan(){
 const generation=wizardGeneration;
 const list=$('#portList');list.textContent='';
 const summary=document.createElement('p');summary.className='port-summary';summary.textContent=t('portChecking');list.appendChild(summary);
 try{
  const report=await request('/api/ports',{source:$('#sourceYaml').value,selected_profiles:activeProfiles()});
  if(generation!==wizardGeneration)return;
  $('#buildDeferred').hidden=true;
  list.textContent='';
  if(!report.ports.length){summary.textContent=t('portNoFixed');list.appendChild(summary);return}
  report.ports.forEach(p=>{
   const row=document.createElement('div');row.className='port-entry'+(p.available?'':' bad');
   const body=document.createElement('div');const title=document.createElement('div');title.className='port-main';
   title.textContent=`${p.service} · ${p.host_port}/${p.protocol.toUpperCase()} → ${p.target_port} · ${t(p.available?'portFree':'portOccupied')}`;
   const desc=document.createElement('div');desc.className='port-explanation';desc.textContent=p.available?t('portFree'):({reserved:t('portReasonReserved'),docker:t('portReasonDocker').replace('{owner}',p.owner||'?'),duplicate:t('portReasonDuplicate'),host:t('portReasonHost')}[p.reason_code]||p.reason);body.append(title,desc);row.appendChild(body);
   if(!p.available&&p.suggestion){const btn=document.createElement('button');btn.type='button';btn.className='secondary';btn.textContent=t('portPortChange').replace('{port}',p.suggestion);
    btn.onclick=()=>changePort(p,btn);row.appendChild(btn)}
   list.appendChild(row);
  });
 }catch(e){if(generation!==wizardGeneration)return;summary.textContent=t('portNotChecked')+' '+errorMessage(e);list.textContent='';list.appendChild(summary);summary.style.color='#ff9e9e'}
}
async function changePort(p,btn){
 btn.disabled=true;
 try{const res=await request('/api/ports/replace',{source:$('#sourceYaml').value,selected_profiles:activeProfiles(),service:p.service,index:p.index,new_port:p.suggestion});
  $('#sourceYaml').value=res.source;showRequiredComposeFields();await refreshSettings();await refreshPortScan();notice(t('portChanged'));
 }catch(e){notice(errorMessage(e),true)}finally{btn.disabled=false}
}
function chosenProfiles(){return $$('#profileList input[data-profile]:checked').map(el=>el.dataset.profile)}
// Defer an optional service until the user supplies its requirements.
// The backend validates this again during preview; no key is ever sent to /api/ports.
function activeProfiles(){return chosenProfiles()}
function updateDeferredHint(){
 if($('#notification').classList.contains('error'))notice('');
 const pending=chosenProfiles().includes('tailscale')&&!$('#tailscaleAuthKey').value.trim();
 $('#tailscaleDeferred').hidden=!pending;
 $('#cloudflareDeferred').hidden=!(chosenProfiles().includes('tunnel')&&!$('#cloudflareTunnelToken').value.trim());
}
function drawProfiles(profiles){
 availableProfiles=Array.isArray(profiles)?profiles:[];
 const wrap=$('#profileReview'),list=$('#profileList');list.replaceChildren();wrap.hidden=!availableProfiles.length;
 $('#buildDeferred').hidden=true;
 for(const item of availableProfiles){
  const label=document.createElement('label');label.className='profile-entry';
  const chk=document.createElement('input');chk.type='checkbox';chk.dataset.profile=item.name;
  const body=document.createElement('span');const title=document.createElement('strong');title.textContent=item.name+' · '+(item.services||[]).join(', ');
  body.appendChild(title);
  if(item.local_build){const sub=document.createElement('small');sub.textContent=t('profileBuild');body.appendChild(sub)}
  label.append(chk,body);chk.addEventListener('change',async()=>{profileAuthVisibility();await refreshPortScan()});list.appendChild(label)
 }
 profileAuthVisibility()
}
function profileAuthVisibility(){
 const required=chosenProfiles().includes('tailscale');$('#tailscaleAuthRow').hidden=!required;
 if(!required)$('#tailscaleAuthKey').value='';
 const cfRequired=chosenProfiles().includes('tunnel');$('#cloudflareAuthRow').hidden=!cfRequired;
 if(!cfRequired)$('#cloudflareTunnelToken').value='';
 updateDeferredHint();
}
function showPublisherSuggestions(items){
 publisherImages=Array.isArray(items)?items.slice():[];
 const box=$('#publisherSuggestions');box.replaceChildren();
 box.hidden=!Array.isArray(items)||!items.length;
 if(box.hidden)return;
 for(const item of items){
  const row=document.createElement('div');row.className='publisher-entry';
  const title=document.createElement('strong');title.textContent=t('publishedImage')+': '+item.service;
  const details=document.createElement('code');details.textContent=item.current+' → '+item.recommended;
  const action=document.createElement('button');action.type='button';action.className='secondary';action.textContent=t('publisherAccept');
  const sourceLink=document.createElement('a');sourceLink.href=item.readme_url;sourceLink.target='_blank';sourceLink.rel='noopener noreferrer';sourceLink.textContent='README';
  action.onclick=async()=>{
   if(action.disabled)return;
   action.disabled=true;
   try{
    const result=await request('/api/source/image',{source:$('#sourceYaml').value,service:item.service,expected_image:item.current,replacement_image:item.recommended});
    $('#sourceYaml').value=result.source;showRequiredComposeFields();
    publisherImages=publisherImages.filter(v=>!(v.service===item.service&&v.current===item.current));
    row.remove();if(!box.children.length)box.hidden=true;
    planReady=false;await refreshPortScan();notice(t('publisherApplied'));
   }catch(e){notice(errorMessage(e),true);action.disabled=false}
  };
  row.append(title,details,action,sourceLink);box.appendChild(row);
 }
}
// v0.2.9: multi-format, multi-theme icon gallery; upstream logos retain priority.
const iconTexts={
 de:{title:'App-Logos auswählen',refresh:'Erneut suchen',search:'Suche in Originalprojekt, Dashboard Icons, selfh.st, Simple Icons und TechIcons …',none:'Keine passenden Logos gefunden. Du kannst weiterhin eine Icon-URL eintragen.',found:'{count} Logo-Treffer. Verfügbare Varianten und Formate auswählen.',limited:'Die Originalprojekt-Suche war eingeschränkt.',selected:'Logo ausgewählt',warning:'Icon-Katalog derzeit nicht erreichbar.',button:'Suchen',placeholder:'Logo suchen (z. B. FreeCAD) …',base:'Original',light:'Hell',dark:'Dunkel',original:'Originalprojekt',detail:'Details',sourceLabel:'Logoquelle',sourceAll:'Alle Quellen',sourceProject:'Originalprojekt',sourceDashboard:'Dashboard Icons',sourceSelfhst:'selfh.st/icons',sourceSimple:'Simple Icons',sourceTechicons:'TechIcons',sourceLink:'selfh.st-Katalog ↗'},
 en:{title:'Choose app icons',refresh:'Search again',search:'Searching project, Dashboard Icons, selfh.st, Simple Icons and TechIcons …',none:'No matching icons. You can still enter an icon URL.',found:'{count} logo matches. Choose available variants and formats.',limited:'Upstream search was limited.',selected:'Icon selected',warning:'Icon catalogue unavailable.',button:'Search',placeholder:'Search icons (e.g. FreeCAD) …',base:'Original',light:'Light',dark:'Dark',original:'Upstream',detail:'Details',sourceLabel:'Icon source',sourceAll:'All sources',sourceProject:'Original project',sourceDashboard:'Dashboard Icons',sourceSelfhst:'selfh.st/icons',sourceSimple:'Simple Icons',sourceTechicons:'TechIcons',sourceLink:'selfh.st catalogue ↗'},
 fr:{title:'Choisir le logo',refresh:'Rechercher',search:'Recherche de logos et variantes …',none:'Aucun logo trouvé.',found:'{count} logos. Choisir la variante et le format.',limited:'Recherche du dépôt limitée.',selected:'Logo sélectionné',warning:'Catalogue indisponible.',button:'Chercher',placeholder:'Chercher un logo …',base:'Original',light:'Clair',dark:'Sombre',original:'Projet original',detail:'Détails',sourceLabel:'Source des logos',sourceAll:'Toutes les sources',sourceProject:'Projet original',sourceDashboard:'Dashboard Icons',sourceSelfhst:'selfh.st/icons',sourceSimple:'Simple Icons',sourceTechicons:'TechIcons',sourceLink:'Catalogue selfh.st ↗'},
 pt:{title:'Escolher logótipo',refresh:'Pesquisar',search:'A procurar logótipos e variantes …',none:'Nenhum logótipo encontrado.',found:'{count} logótipos. Escolha a variante e o formato.',limited:'Pesquisa limitada.',selected:'Logótipo escolhido',warning:'Catálogo indisponível.',button:'Pesquisar',placeholder:'Pesquisar logótipos …',base:'Original',light:'Claro',dark:'Escuro',original:'Projeto original',detail:'Detalhes',sourceLabel:'Origem dos ícones',sourceAll:'Todas as origens',sourceProject:'Projeto original',sourceDashboard:'Dashboard Icons',sourceSelfhst:'selfh.st/icons',sourceSimple:'Simple Icons',sourceTechicons:'TechIcons',sourceLink:'Catálogo selfh.st ↗'},
 es:{title:'Elegir logo',refresh:'Buscar',search:'Buscando logos y variantes …',none:'No se encontraron logos.',found:'{count} logos. Elija variante y formato.',limited:'Búsqueda limitada.',selected:'Logo elegido',warning:'Catálogo no disponible.',button:'Buscar',placeholder:'Buscar logos …',base:'Original',light:'Claro',dark:'Oscuro',original:'Proyecto original',detail:'Detalles',sourceLabel:'Origen de iconos',sourceAll:'Todas las fuentes',sourceProject:'Proyecto original',sourceDashboard:'Dashboard Icons',sourceSelfhst:'selfh.st/icons',sourceSimple:'Simple Icons',sourceTechicons:'TechIcons',sourceLink:'Catálogo selfh.st ↗'}
};
const it=k=>(iconTexts[lang]||iconTexts.de)[k];
let iconProjectUrl='',iconOptions=[],iconLimited=false,iconCatalogWarning='',iconSearchGeneration=0,iconSearchTerms=[];
function renderIconPicker(){
 const panel=$('#iconPicker');panel.hidden=!(iconSearchTerms.length||iconProjectUrl||$('#iconSearchInput').value.trim());
 if(panel.hidden)return;
 $('#iconPickerTitle').textContent=it('title');$('#iconRescan').textContent=it('refresh');
 $('#iconSearchSubmit').textContent=it('button');$('#iconSearchInput').placeholder=it('placeholder');
 $('#iconSourceLabel').textContent=it('sourceLabel');
 const link=$('#selfhstCatalogLink');
 const selectedSource=$('#iconSourceFilter').value||'all';
 const catalogPages={dashboardicons:['https://dashboardicons.com/','Dashboard Icons ↗'],selfhst:['https://selfh.st/icons/','selfh.st/icons ↗'],simpleicons:['https://simpleicons.org/','Simple Icons ↗'],techicons:['https://techicons.dev/','TechIcons ↗']};
 const selectedPage=catalogPages[selectedSource];
 link.hidden=!selectedPage;
 if(selectedPage){link.href=selectedPage[0];link.textContent=selectedPage[1];}
 for(const [value,key] of [['all','sourceAll'],['project','sourceProject'],['dashboardicons','sourceDashboard'],['selfhst','sourceSelfhst'],['simpleicons','sourceSimple'],['techicons','sourceTechicons']]){
  const option=$('#iconSourceFilter').querySelector(`option[value="${value}"]`);if(option)option.textContent=it(key);
 }

 const grid=$('#iconPickerGrid');grid.replaceChildren();const status=$('#iconPickerStatus');
 if(iconOptions.length){status.textContent=it('found').replace('{count}',String(iconOptions.length))+(iconLimited?' '+it('limited'):'')+(iconCatalogWarning?' '+iconCatalogWarning:'');}
 else if(!status.dataset.loading){status.textContent=it('none')+(iconCatalogWarning?' '+iconCatalogWarning:'');}
 const current=$('#iconUrl').value.trim();
 for(const item of iconOptions){
  const card=document.createElement('article');card.className='im-icon-result';
  const header=document.createElement('div');header.className='im-icon-result-head';
  const name=document.createElement('strong');name.textContent=item.path;
  const origin=document.createElement('span');origin.textContent=item.source_label||it('original');origin.className='im-icon-result-source';
  header.append(name,origin);card.appendChild(header);
  const variants=Array.isArray(item.variants)&&item.variants.length?item.variants:[{theme:'base',format:item.format||'PNG',url:item.url}];
  for(const theme of ['base','light','dark']){
   const available=variants.filter(v=>v.theme===theme);
   if(!available.length)continue;
   const row=document.createElement('div');row.className='im-icon-variant';row.dataset.theme=theme;
   const desc=document.createElement('span');desc.className='im-icon-variant-label';desc.textContent=it(theme);
   const preview=document.createElement('img');preview.alt=`${item.path} ${it(theme)}`;preview.loading='lazy';preview.decoding='async';preview.referrerPolicy='no-referrer';
   const thumb=available.find(v=>v.format==='PNG')||available.find(v=>v.format==='SVG')||available[0];preview.src=thumb.url;
   const formats=document.createElement('div');formats.className='im-icon-formats';
   for(const variant of available){
    const button=document.createElement('button');button.type='button';button.className='im-icon-format-button';button.textContent=variant.label?`${variant.format} · ${variant.label}`:variant.format;
    const selected=current===variant.url;button.classList.toggle('im-icon-selected',selected);button.setAttribute('aria-pressed',String(selected));
    button.title=`${item.path} · ${it(theme)} · ${variant.format}`;
    button.onclick=()=>{$('#iconUrl').value=variant.url;$('#iconUrl').dispatchEvent(new Event('input',{bubbles:true}));};
    formats.appendChild(button);
   }
   row.append(desc,preview,formats);card.appendChild(row);
  }
  if(item.detail_url){const link=document.createElement('a');link.href=item.detail_url;link.target='_blank';link.rel='noopener noreferrer';link.className='im-icon-detail-link';link.textContent=it('detail')+' ↗';card.appendChild(link)}
  grid.appendChild(card);
 }
}
async function searchProjectIcons(projectUrl='',forceRefresh=false,searchQuery=''){
 const token=++iconSearchGeneration;iconProjectUrl=projectUrl;
 iconOptions=[];iconLimited=false;iconCatalogWarning='';renderIconPicker();
 if(!iconSearchTerms.length&&!projectUrl&&!searchQuery)return;
 const status=$('#iconPickerStatus');status.dataset.loading='yes';status.textContent=it('search');
 const rescan=$('#iconRescan'),submit=$('#iconSearchSubmit');rescan.disabled=true;submit.disabled=true;
 const existingIcon=$('#iconUrl').value;
 try{
  const result=await request('/api/icons/search',{project_url:projectUrl,terms:iconSearchTerms,query:searchQuery,refresh:forceRefresh,source:$('#iconSourceFilter').value||'all'});
  if(token!==iconSearchGeneration)return;
  iconOptions=Array.isArray(result.icons)?result.icons:[];
  iconLimited=!!result.limited;iconCatalogWarning=result.catalog_warning||'';
  const auto=iconOptions.find(x=>x.origin==='project')||iconOptions.find(x=>x.origin==='dashboardicons'&&x.score>=900)||iconOptions.find(x=>x.origin==='selfhst'&&x.score>=900)||iconOptions.find(x=>x.origin==='simpleicons'&&x.score>=900)||iconOptions.find(x=>x.origin==='techicons'&&x.score>=900);
  if(!searchQuery&&auto&&$('#iconUrl').value===existingIcon&&!existingIcon.trim()){$('#iconUrl').value=auto.url;}
  delete status.dataset.loading;renderIconPicker();
 }catch(e){if(token!==iconSearchGeneration)return;iconOptions=[];delete status.dataset.loading;renderIconPicker();status.textContent=errorMessage(e)}
 finally{if(token===iconSearchGeneration){rescan.disabled=false;submit.disabled=false}}
}
function resetProjectIcons(){++iconSearchGeneration;iconProjectUrl='';iconSearchTerms=[];iconOptions=[];iconLimited=false;iconCatalogWarning='';$('#iconPicker').hidden=true;$('#iconPickerGrid').replaceChildren();$('#iconSearchInput').value='';$('#iconSourceFilter').value='all';}

// NAS folder browsing and local credential editing; deliberately read-only
// host volumes and no persistence of credentials in localStorage.
const configureText={
 de:{network:'Host-Port und Erreichbarkeit',networkHint:'Neue Web-Apps: Heimnetzzugriff ist der Standard. Nur NAS bleibt wählbar. 0.0.0.0 bindet alle IPv4-Schnittstellen; NAS-Firewall beachten.',loopback:'Nur NAS (127.0.0.1)',lan:'Heimnetz (0.0.0.0)',shared:'gemeinsam mit',fixedFormat:'Anwendungsformat: 32 Zufallsbytes als Base64 (44 Zeichen)',hexFormat:'Hexadezimaler Schlüssel; Länge nur gerade Werte',differentKeys:'Einige gleichnamige Secrets unterscheiden sich zwischen Diensten; Werte werden nicht zusammengeführt.',choose:'Ordner wählen',browse:'NAS-Ordner auswählen',use:'Diesen Ordner verwenden',back:'Zurück',unavailable:'Keine lesbaren NAS-Verzeichnisse. Bitte docker-compose.override.yml installieren und den Container neu erstellen.',empty:'Keine Unterordner',truncated:'Maximal 500 Ordner angezeigt',settings:'Zugangsdaten und NAS-Freigaben',hint:'Vor der Installation Benutzername, lokale Passwörter und Host-Pfade anpassen. Werte werden in die Compose-Vorschau übernommen.',apply:'Übernehmen',regenerate:'Neu erzeugen',stored:'In Compose eingetragen. Bitte die fertige Konfiguration sicher aufbewahren.',secret:'Schlüssel/Passwort',user:'Benutzername',mount:'Host-Ordner',passwordHint:'Externe API-Tokens müssen weiterhin beim jeweiligen Anbieter erstellt werden.',prompt:'Vor der Installation festlegen',required:'Erforderlich – noch kein Wert eingetragen',recommended:'Bitte für diese Anwendung ein Passwort oder einen Schlüssel vergeben.',length:'Länge',lowercase:'Kleinbuchstaben (a–z)',uppercase:'Großbuchstaben (A–Z)',digits:'Zahlen (0–9)',symbols:'Sonderzeichen',show:'Anzeigen',hide:'Verbergen',emptyWarn:'Passwort oder Secret fehlt. Bitte die markierten Felder ausfüllen oder erzeugen.',generator:'Generator-Einstellungen',notSaved:'Zugangsdaten stehen in der Compose-Datei; die Datei sicher aufbewahren.'},
 en:{network:'Host port and accessibility',networkHint:'New Web apps default to LAN access. NAS only remains available. 0.0.0.0 listens on all IPv4 interfaces; check your NAS firewall.',loopback:'NAS only (127.0.0.1)',lan:'LAN (0.0.0.0)',shared:'shared with',fixedFormat:'Application format: 32 random bytes as Base64 (44 chars)',hexFormat:'Hexadecimal key; length must be even',differentKeys:'Some identically named secrets differ between services; values are not merged.',choose:'Browse folders',browse:'Choose NAS folder',use:'Use this folder',back:'Back',unavailable:'No readable NAS directories. Install docker-compose.override.yml and recreate the container.',empty:'No subfolders',truncated:'Showing at most 500 directories',settings:'Credentials and NAS folders',hint:'Change usernames, local passwords and host paths before installation. Values are included in the Compose preview.',apply:'Apply',regenerate:'Regenerate',stored:'Saved in Compose. Keep the generated configuration safe.',secret:'Secret/password',user:'Username',mount:'Host folder',passwordHint:'External API tokens must be issued by the provider.',prompt:'Set before installation',required:'Required – no value assigned yet',recommended:'Set a password or secret before installing this application.',length:'Length',lowercase:'Lowercase (a–z)',uppercase:'Uppercase (A–Z)',digits:'Numbers (0–9)',symbols:'Special characters',show:'Show',hide:'Hide',emptyWarn:'A password or secret is missing. Fill or generate the highlighted values.',generator:'Generator settings',notSaved:'Credentials are included in Compose; keep the file secure.'},
 fr:{network:'Port hôte et accès',networkHint:'Les nouvelles apps Web utilisent le LAN par défaut. NAS seul reste possible. 0.0.0.0 écoute sur toutes les interfaces IPv4 : vérifier le pare-feu.',loopback:'NAS seul (127.0.0.1)',lan:'Réseau local (0.0.0.0)',shared:'partagé avec',fixedFormat:'Format requis : 32 octets aléatoires Base64 (44 caractères)',hexFormat:'Clé hexadécimale; longueur paire',differentKeys:'Des secrets homonymes diffèrent entre services; ils ne seront pas fusionnés.',choose:'Choisir un dossier',browse:'Dossiers du NAS',use:'Utiliser ce dossier',back:'Retour',unavailable:'Dossiers indisponibles. Installer docker-compose.override.yml et recréer le conteneur.',empty:'Aucun sous-dossier',truncated:'500 dossiers au maximum',settings:'Identifiants et dossiers du NAS',hint:'Configurer utilisateurs, mots de passe locaux et chemins avant installation.',apply:'Appliquer',regenerate:'Régénérer',stored:'Enregistré dans Compose. Garder la configuration en lieu sûr.',secret:'Secret/mot de passe',user:'Utilisateur',mount:'Dossier hôte',passwordHint:'Les jetons API externes doivent venir du fournisseur.',prompt:'À définir avant installation',required:'Obligatoire – valeur manquante',recommended:'Définissez un mot de passe ou une clé.',length:'Longueur',lowercase:'Minuscules (a–z)',uppercase:'Majuscules (A–Z)',digits:'Chiffres (0–9)',symbols:'Caractères spéciaux',show:'Afficher',hide:'Masquer',emptyWarn:'Mot de passe ou clé manquante. Complétez les champs signalés.',generator:'Options de génération',notSaved:'Les identifiants figurent dans Compose. Conservez le fichier en lieu sûr.'},
 pt:{network:'Porta do host e acesso',networkHint:'Novas apps Web usam a rede local por defeito. Só NAS continua disponível. 0.0.0.0 escuta em todas as interfaces IPv4; confirme a firewall.',loopback:'Só NAS (127.0.0.1)',lan:'Rede local (0.0.0.0)',shared:'partilhado com',fixedFormat:'Formato exigido: 32 bytes aleatórios Base64 (44 caracteres)',hexFormat:'Chave hexadecimal; comprimento par',differentKeys:'Algumas chaves com o mesmo nome têm valores diferentes; não serão unificadas.',choose:'Escolher pasta',browse:'Pastas do NAS',use:'Usar esta pasta',back:'Voltar',unavailable:'Pastas não disponíveis. Instale docker-compose.override.yml e recrie o contentor.',empty:'Sem subpastas',truncated:'Mostradas até 500 pastas',settings:'Credenciais e pastas do NAS',hint:'Configure utilizadores, palavras-passe locais e caminhos antes de instalar.',apply:'Aplicar',regenerate:'Gerar novamente',stored:'Guardado no Compose. Guarde a configuração em segurança.',secret:'Chave/palavra-passe',user:'Utilizador',mount:'Pasta de origem',passwordHint:'Os tokens de API externos devem ser emitidos pelo fornecedor.',prompt:'Definir antes de instalar',required:'Obrigatório – valor em falta',recommended:'Defina uma palavra-passe ou chave para esta aplicação.',length:'Comprimento',lowercase:'Minúsculas (a–z)',uppercase:'Maiúsculas (A–Z)',digits:'Números (0–9)',symbols:'Caracteres especiais',show:'Mostrar',hide:'Ocultar',emptyWarn:'Falta uma palavra-passe ou chave. Preencha ou gere os campos indicados.',generator:'Opções do gerador',notSaved:'As credenciais ficam no Compose. Guarde o ficheiro em segurança.'},
 es:{network:'Puerto del host y acceso',networkHint:'Las nuevas apps web usan la red local de forma predeterminada. Solo NAS sigue disponible. 0.0.0.0 escucha en todas las interfaces IPv4; comprueba el cortafuegos.',loopback:'Solo NAS (127.0.0.1)',lan:'Red local (0.0.0.0)',shared:'compartido con',fixedFormat:'Formato requerido: 32 bytes aleatorios Base64 (44 caracteres)',hexFormat:'Clave hexadecimal; longitud par',differentKeys:'Algunos secretos con el mismo nombre tienen valores distintos; no se fusionan.',choose:'Elegir carpeta',browse:'Carpetas NAS',use:'Usar esta carpeta',back:'Atrás',unavailable:'Carpetas no disponibles. Instale docker-compose.override.yml y vuelva a crear el contenedor.',empty:'Sin subcarpetas',truncated:'Hasta 500 carpetas',settings:'Credenciales y carpetas NAS',hint:'Configure usuarios, contraseñas locales y rutas antes de instalar.',apply:'Aplicar',regenerate:'Regenerar',stored:'Guardado en Compose. Conserve la configuración de forma segura.',secret:'Clave/contraseña',user:'Usuario',mount:'Carpeta origen',passwordHint:'Los tokens API externos deben obtenerse del proveedor.',prompt:'Configurar antes de instalar',required:'Obligatorio – falta el valor',recommended:'Configure una contraseña o clave.',length:'Longitud',lowercase:'Minúsculas (a–z)',uppercase:'Mayúsculas (A–Z)',digits:'Números (0–9)',symbols:'Caracteres especiales',show:'Mostrar',hide:'Ocultar',emptyWarn:'Falta una contraseña o clave. Complete o genere los campos marcados.',generator:'Opciones del generador',notSaved:'Las credenciales se incluyen en Compose. Guarde el archivo de forma segura.'}
};
const ct=k=>(configureText[lang]||configureText.de)[k];
let folderCurrent='',folderSelection=null,settingsTimer=null,settingsGeneration=0;
async function loadFolder(path){
 const msg=$('#folderBrowseMessage'),list=$('#folderBrowseItems');
 msg.textContent='';list.replaceChildren();
 try{
  const res=await request('/api/nas/folders',{path});folderCurrent=res.path;
  $('#folderBrowsePath').textContent=res.path||'/';
  $('#folderBrowseSelect').disabled=!res.selectable;
  const folders=res.folders||[];
  for(const folder of folders){
   const btn=document.createElement('button');btn.type='button';btn.textContent='▸  '+folder.name;
   btn.onclick=()=>loadFolder(folder.path);list.appendChild(btn);
  }
  if(!folders.length)msg.textContent=path?ct('empty'):ct('unavailable');
  if(res.truncated)msg.textContent+=' '+ct('truncated');
 }catch(e){msg.textContent=errorMessage(e);$('#folderBrowseSelect').disabled=true;}
}
async function openFolderPicker(onPick,startPath=''){
 folderSelection=onPick;
 $('#folderDialogHeading').textContent=ct('browse');
 $('#folderBrowseSelect').textContent=ct('use');$('#folderBrowseBack').textContent=ct('back');
 $('#folderDialog').showModal();
 await loadFolder('');
 if(startPath.startsWith('/DATA')||startPath.startsWith('/media')){
  try{await loadFolder(startPath)}catch(e){} // Invalid path remains selectable through root listing.
 }
}
function scheduleSettings(){clearTimeout(settingsTimer);settingsTimer=setTimeout(refreshSettings,400);}
async function modifySetting(payload){
 try{
  const result=await request('/api/compose/modify',{source:$('#sourceYaml').value,...payload});
  $('#sourceYaml').value=result.source;planReady=false;
  showRequiredComposeFields();await refreshSettings();await refreshPortScan();
  notice(ct('stored'));
 }catch(e){notice(errorMessage(e),true)}
}
const accessLang={
 de:{title:'Benutzer und Berechtigungen',description:'Pro Dienst wählen. Automatisch nutzt den Standardbenutzer des Images. Root nur bei begründetem Bedarf.',auto:'Automatisch (Image-Standard)',normal:'Benutzer 1000:1000',root:'Root (0:0)',custom:'Eigene UID/GID',apply:'Übernehmen',warning:'Root ermöglicht weitreichenden Zugriff auf eingebundene Host-Ordner.',mounts:'NAS-Ordnerzugriff',read:'Nur Lesen',write:'Lesen und Schreiben',updated:'Berechtigungen in die Quell-Compose übernommen.'},
 en:{title:'Users and permissions',description:'Configure each service. Automatic uses the image default. Root only when necessary.',auto:'Automatic (image default)',normal:'User 1000:1000',root:'Root (0:0)',custom:'Custom UID/GID',apply:'Apply',warning:'Root has extensive access to mounted host folders.',mounts:'NAS folder access',read:'Read only',write:'Read and write',updated:'Permissions updated in source Compose.'},
 fr:{title:'Utilisateurs et autorisations',description:'Choisir par service. Automatique utilise les paramètres de l’image.',auto:'Automatique',normal:'Utilisateur 1000:1000',root:'Root (0:0)',custom:'UID/GID personnalisés',apply:'Appliquer',warning:'Root donne un accès étendu aux dossiers montés.',mounts:'Accès aux dossiers',read:'Lecture seule',write:'Lecture et écriture',updated:'Autorisations mises à jour.'},
 pt:{title:'Utilizadores e permissões',description:'Configurar por serviço. Automático usa o padrão da imagem.',auto:'Automático',normal:'Utilizador 1000:1000',root:'Root (0:0)',custom:'UID/GID personalizado',apply:'Aplicar',warning:'Root permite acesso alargado às pastas montadas.',mounts:'Acesso às pastas',read:'Só leitura',write:'Leitura e escrita',updated:'Permissões atualizadas.'},
 es:{title:'Usuarios y permisos',description:'Configurar cada servicio. Automático usa el usuario predeterminado de la imagen.',auto:'Automático',normal:'Usuario 1000:1000',root:'Root (0:0)',custom:'UID/GID propios',apply:'Aplicar',warning:'Root permite acceso amplio a carpetas montadas.',mounts:'Acceso a carpetas',read:'Solo lectura',write:'Lectura y escritura',updated:'Permisos actualizados.'}
};
const at=k=>(accessLang[lang]||accessLang.de)[k];
async function updateAccess(payload){
 try{const res=await request('/api/compose/access',{source:$('#sourceYaml').value,...payload});
 $('#sourceYaml').value=res.source;planReady=false;showRequiredComposeFields();await refreshSettings();await refreshPortScan();notice(at('updated'));
 }catch(e){notice(errorMessage(e),true)}
}
function renderAccess(services){
 const box=$('#accessPanel');box.replaceChildren();box.hidden=!services.length;
 if(box.hidden)return;
 const heading=document.createElement('strong');heading.textContent=at('title');box.appendChild(heading);
 const hint=document.createElement('p');hint.className='field-note';hint.textContent=at('description');box.appendChild(hint);
 for(const svc of services){
  const section=document.createElement('div');section.className='im-access-service';
  const title=document.createElement('strong');title.textContent=svc.name;section.appendChild(title);
  const row=document.createElement('div');row.className='im-access-choice';
  const select=document.createElement('select');
  for(const [value,label] of [['automatic','auto'],['normal','normal'],['root','root'],['custom','custom']]){
   const opt=document.createElement('option');opt.value=value;opt.textContent=at(label);select.appendChild(opt);
  }
  const match=/^(\d+):(\d+)$/.exec(svc.user);
  select.value=!svc.user?'automatic':svc.user==='0:0'?'root':svc.user==='1000:1000'?'normal':'custom';
  const uid=document.createElement('input'),gid=document.createElement('input');
  for(const field of [uid,gid]){field.type='number';field.min='0';field.max='2147483647';}
  uid.value=match?.[1]||'1000';gid.value=match?.[2]||'1000';uid.title='UID';gid.title='GID';
  const warning=document.createElement('small');warning.textContent=at('warning');warning.style.color='#ffb06e';
  const refresh=()=>{uid.hidden=gid.hidden=select.value!=='custom';warning.hidden=select.value!=='root'};
  select.onchange=refresh;refresh();
  const apply=document.createElement('button');apply.type='button';apply.className='secondary';apply.textContent=at('apply');
  apply.onclick=()=>{const u=Number(uid.value),g=Number(gid.value);if(select.value==='custom'&&(!Number.isInteger(u)||!Number.isInteger(g)||u<0||g<0||u>2147483647||g>2147483647)){notice(t('invalid'),true);return}updateAccess({service:svc.name,mode:select.value,uid:u,gid:g})};
  row.append(select,uid,gid,apply);section.append(row,warning);
  if(svc.mounts?.length){const lbl=document.createElement('p');lbl.className='field-note';lbl.textContent=at('mounts');section.appendChild(lbl)}
  for(const m of svc.mounts||[]){const mount=document.createElement('div');mount.className='im-access-mount';
   const name=document.createElement('code');name.textContent=m.source+' → '+m.target;
   const access=document.createElement('select');for(const [v,label] of [['ro','read'],['rw','write']]){const o=document.createElement('option');o.value=v;o.textContent=at(label);access.appendChild(o)}
   access.value=m.read_only?'ro':'rw';access.onchange=()=>updateAccess({service:svc.name,mode:'mount',index:m.index,read_only:access.value==='ro'});
   mount.append(name,access);section.appendChild(mount);
  }
  box.appendChild(section);
 }
}

function missingSecretsInEditor(){
 const panel=$('#composeSettingsPanel');
 return [...panel.querySelectorAll('.im-settings-row.im-credential-missing')].length;
}
async function setNetworkExposure(service,index,exposure){
 try{
  const updated=await request('/api/compose/network',{source:$('#sourceYaml').value,service,index,exposure});
  $('#sourceYaml').value=updated.source;planReady=false;
  showRequiredComposeFields();await refreshSettings();await refreshPortScan();
  notice(ct('stored'));
 }catch(e){notice(errorMessage(e),true);await refreshSettings()}
}
async function refreshSettings(){
 const generation=++settingsGeneration,box=$('#composeSettingsPanel');
 let result;
 try{result=await request('/api/compose/settings',{kind:'yaml',value:$('#sourceYaml').value})}
 catch(e){if(generation===settingsGeneration)box.hidden=true;return}
 if(generation!==settingsGeneration)return;
 box.replaceChildren();
  const urls=result.app_urls||[];
 const cred=result.credentials||[],mounts=result.mounts||[],networkPorts=result.network_ports||[];renderAccess(result.access_services||[]);
 box.hidden=!cred.length&&!mounts.length&&!urls.length&&!networkPorts.length;if(box.hidden)return;
 const heading=document.createElement('strong');heading.textContent=ct('settings');box.appendChild(heading);
 const hint=document.createElement('p');hint.className='field-note';hint.textContent=ct('hint');box.appendChild(hint);
 for(const warning of result.credential_warnings||[]){const msg=document.createElement('p');msg.className='field-note';msg.textContent=ct('differentKeys')+' ('+warning.split(':')[0]+')';box.appendChild(msg)}
 if(networkPorts.length){
  const title=document.createElement('strong');title.textContent=ct('network');box.appendChild(title);
  const help=document.createElement('p');help.className='field-note';help.textContent=ct('networkHint');box.appendChild(help);
  for(const item of networkPorts){
   const row=document.createElement('div');row.className='im-settings-row';
   const label=document.createElement('div');label.className='im-settings-head';label.textContent=item.service+' · '+'Port'+' '+item.host_port;row.appendChild(label);
   const access=document.createElement('select');for(const [value,label] of [['loopback','loopback'],['lan','lan']]){const option=document.createElement('option');option.value=value;option.textContent=ct(label);access.appendChild(option)}
   access.value=item.exposure;access.onchange=()=>setNetworkExposure(item.service,item.index,access.value);row.appendChild(access);box.appendChild(row);
  }
 }
  if(urls.length){
   const heading=document.createElement('strong');heading.textContent=({de:'App-Adresse und Netzwerk',en:'Application URL and network',fr:'Adresse de l’application',pt:'Endereço da aplicação',es:'Dirección de la aplicación'}[lang]||'App-Adresse und Netzwerk');box.appendChild(heading);
   const help=document.createElement('p');help.className='field-note';help.textContent=({de:'Tatsächliche Adresse für den späteren Zugriff eingeben. Platzhalter wie https://your-domain.com sind nicht installierbar.',en:'Enter the real application URL. Placeholder domains are not accepted.',fr:'Indiquez la véritable adresse de l’application.',pt:'Introduza o endereço real da aplicação.',es:'Introduzca la dirección real de la aplicación.'}[lang]||'App-Adresse eingeben.');box.appendChild(help);
   for(const item of urls){
    const row=document.createElement('div');row.className='im-settings-row';if(item.required)row.classList.add('im-credential-missing');
    const label=document.createElement('div');label.className='im-settings-head';label.textContent=item.service+' · '+item.key;row.appendChild(label);
    const actions=document.createElement('div');actions.className='im-field-row';
    const input=document.createElement('input');input.type='url';input.value=item.value;input.placeholder='http://NAS-IP:3000';input.spellcheck=false;input.autocomplete='off';
    const save=document.createElement('button');save.type='button';save.className='secondary';save.textContent=ct('apply');
    save.onclick=async()=>{try{const result=await request('/api/compose/app-url',{source:$('#sourceYaml').value,service:item.service,key:item.key,value:input.value.trim()});$('#sourceYaml').value=result.source;planReady=false;showRequiredComposeFields();await refreshSettings();await refreshPortScan();}catch(e){notice(errorMessage(e),true)}};
    actions.append(input,save);row.appendChild(actions);box.appendChild(row);
   }
  }
 for(const item of cred){
  const row=document.createElement('div');row.className='im-settings-row';
  if(item.required)row.classList.add('im-credential-missing');
  const label=document.createElement('div');label.className='im-settings-head';label.textContent=`${(item.services?.length>1?item.services.join(', '):item.service)} · ${item.key} (${ct(item.secret?'secret':'user')})`;
  if(item.required){const warn=document.createElement('span');warn.className='im-required';warn.textContent=ct('required');label.append(' · ',warn)}
  const actions=document.createElement('div');actions.className='im-field-row';
  const input=document.createElement('input');input.type=item.secret?'password':'text';input.autocomplete='off';input.spellcheck=false;input.value=item.value;
  input.setAttribute('aria-label',`${item.service} ${item.key}`);
  const apply=document.createElement('button');apply.type='button';apply.className='secondary';apply.textContent=ct('apply');
  apply.onclick=()=>modifySetting({action:'environment',service:item.service,key:item.key,value:input.value});
  actions.append(input);
  if(item.secret){
   const toggle=document.createElement('button');toggle.type='button';toggle.className='secondary';toggle.textContent=ct('show');
   toggle.onclick=()=>{input.type=input.type==='password'?'text':'password';toggle.textContent=ct(input.type==='password'?'show':'hide')};
   actions.append(toggle);
  }
  actions.append(apply);
  row.append(label,actions);
  if(item.secret&&item.spec?.mode==='external'){
   const info=document.createElement('p');info.className='field-note';info.textContent=ct('passwordHint');row.appendChild(info);
  }else if(item.secret){
   const options=document.createElement('details');options.className='im-generator';
   const title=document.createElement('summary');title.textContent=ct('generator');options.appendChild(title);
   const prefs=document.createElement('div');prefs.className='im-generator-options';
   const lengthLabel=document.createElement('label');lengthLabel.textContent=ct('length')+' ';
   const length=document.createElement('input');length.type='number';length.min='12';length.max='128';length.step='1';length.value=item.spec?.length||24;length.step=item.spec?.mode==='hex'?'2':'1';length.disabled=!!item.spec?.fixed;
   lengthLabel.appendChild(length);prefs.appendChild(lengthLabel);
   const checkboxes={};
   for(const [key,checked] of [['lowercase',true],['uppercase',true],['digits',true],['symbols',!item.key.toUpperCase().includes('KEY')]]){
    const line=document.createElement('label');const check=document.createElement('input');check.type='checkbox';check.checked=checked;checkboxes[key]=check;
    if(item.spec?.mode==='hex'||item.spec?.fixed){check.checked=key==='lowercase'||key==='digits';check.disabled=true}
    line.append(check,document.createTextNode(' '+ct(key)));prefs.appendChild(line);
   }
   if(item.spec?.fixed||item.spec?.mode==='hex'){const info=document.createElement('p');info.className='field-note';info.textContent=ct(item.spec?.fixed?'fixedFormat':'hexFormat');prefs.appendChild(info)}
   const generate=document.createElement('button');generate.type='button';generate.className='secondary';generate.textContent=ct('regenerate');
   generate.onclick=()=>{
    const n=Number(length.value);
    if(!Number.isInteger(n)||n<12||n>128||(item.spec?.mode==='hex'&&n%2!==0)||!Object.values(checkboxes).some(c=>c.checked)){
     notice(ct('length')+': 12–128 · '+ct('generator'),true);return;
    }
    modifySetting({action:'environment',service:item.service,key:item.key,generate:true,length:n,
     lowercase:checkboxes.lowercase.checked,uppercase:checkboxes.uppercase.checked,digits:checkboxes.digits.checked,symbols:checkboxes.symbols.checked});
   };
   actions.appendChild(generate);options.appendChild(prefs);row.appendChild(options);
  }else{
   const generate=document.createElement('button');generate.type='button';generate.className='secondary';generate.textContent=ct('regenerate');
   generate.onclick=()=>modifySetting({action:'environment',service:item.service,key:item.key,generate:true});actions.append(generate);
  }
  box.appendChild(row);
 }
 const mountHelp={
  de:{file:'Beispielpfad: Vor dem Übernehmen eine echte Konfigurationsdatei auf dem NAS anlegen.',folder:'Beispielpfad: Gültigen NAS-Ordner unter /DATA/AppData/ eintragen.',existing:'Datei-Mount: Die Datei muss auf dem NAS existieren. Install Monitor erzeugt keine leere Konfigurationsdatei.'},
  en:{file:'Example path: Create a real config file on your NAS before applying.',folder:'Example path: Choose a real NAS folder under /DATA/AppData/.',existing:'File mount: The file must exist on the NAS. Install Monitor will not create an empty configuration file.'},
  fr:{file:'Chemin d’exemple : créez un vrai fichier de configuration sur le NAS avant de valider.',folder:'Chemin d’exemple : choisissez un dossier NAS sous /DATA/AppData/.',existing:'Montage de fichier : le fichier doit exister sur le NAS. Aucun fichier vide ne sera créé.'},
  pt:{file:'Caminho de exemplo: crie primeiro um ficheiro de configuração real no NAS.',folder:'Caminho de exemplo: indique uma pasta válida em /DATA/AppData/.',existing:'Montagem de ficheiro: o ficheiro tem de existir no NAS. Não será criado um ficheiro vazio.'},
  es:{file:'Ruta de ejemplo: cree primero un archivo de configuración real en el NAS.',folder:'Ruta de ejemplo: indique una carpeta válida en /DATA/AppData/.',existing:'Montaje de archivo: debe existir en el NAS. No se creará un archivo vacío.'}
 };
 const mh=mountHelp[lang]||mountHelp.de;
 for(const item of mounts){
  const row=document.createElement('div');row.className='im-settings-row';
  const label=document.createElement('div');label.className='im-settings-head';label.textContent=`${item.service} · ${ct('mount')} → ${item.target}`;
  const actions=document.createElement('div');actions.className='im-field-row';
  const input=document.createElement('input');input.value=item.source;
  const isFile=Boolean(item.file),isPlaceholder=Boolean(item.placeholder);
  // Real configuration files need a path, not the directory picker.
  input.readOnly=!isFile&&!isPlaceholder;
  input.spellcheck=false;
  input.placeholder=isFile?'/DATA/AppData/argus/config.yml':'/DATA/AppData/app/data';
  if(isFile||isPlaceholder){
   const apply=document.createElement('button');apply.type='button';apply.className='secondary';apply.textContent=ct('apply');
   apply.onclick=()=>modifySetting({action:'mount',service:item.service,index:item.index,value:input.value.trim()});
   actions.append(input,apply);
   if(isPlaceholder){const help=document.createElement('p');help.className='field-note';
    help.textContent=isFile?mh.file:mh.folder;
    row.append(label,actions,help);box.appendChild(row);continue;}
   if(isFile){const help=document.createElement('p');help.className='field-note';
    help.textContent=mh.existing;
    row.append(label,actions,help);box.appendChild(row);continue;}
  }else{
   const browse=document.createElement('button');browse.type='button';browse.className='secondary';browse.textContent=ct('choose');
   browse.onclick=()=>openFolderPicker(path=>modifySetting({action:'mount',service:item.service,index:item.index,value:path}),item.source);
   actions.append(input,browse);
  }
  row.append(label,actions);box.appendChild(row);
 }
 const footer=document.createElement('p');footer.className='field-note';footer.textContent=ct('passwordHint');box.appendChild(footer);
}

// Resolve publisher-required Compose variables with explicit user input.
// Never infer MEDIA_ROOT or other existing host paths, and never persist the
// selected values in browser storage. The editor remains the source of truth.
const requiredText={
 de:{title:'Erforderliche Compose-Werte',caption:'Die Originaldatei benötigt diese Angaben. Vorhandene NAS-Pfade oder eigene Werte eintragen.',media:'Medienordner auf dem NAS (MEDIA_ROOT)',value:'Für die Installation erforderlicher Wert',enter:'Wert eintragen',apply:'Wert übernehmen',empty:'Bitte zuerst {name} eintragen.',path:'MEDIA_ROOT muss ein vorhandener absoluter NAS-Ordner sein.'},
 en:{title:'Required Compose values',caption:'The original Compose needs these values. Enter existing NAS paths or your own values.',media:'NAS media folder (MEDIA_ROOT)',value:'Required installation value',enter:'Enter a value',apply:'Apply value',empty:'Please enter {name} first.',path:'MEDIA_ROOT must be an existing absolute NAS folder.'},
 fr:{title:'Valeurs Compose requises',caption:'Indiquez les chemins existants sur le NAS ou vos propres valeurs.',media:'Dossier multimédia du NAS (MEDIA_ROOT)',value:'Valeur requise',enter:'Saisir une valeur',apply:'Appliquer',empty:'Saisissez {name}.',path:'MEDIA_ROOT doit être un dossier absolu existant sur le NAS.'},
 pt:{title:'Valores Compose obrigatórios',caption:'Indique os caminhos existentes no NAS ou os seus próprios valores.',media:'Pasta multimédia no NAS (MEDIA_ROOT)',value:'Valor obrigatório',enter:'Introduzir valor',apply:'Aplicar valor',empty:'Introduza primeiro {name}.',path:'MEDIA_ROOT tem de ser uma pasta absoluta existente no NAS.'},
 es:{title:'Valores Compose obligatorios',caption:'Introduzca rutas existentes del NAS o sus propios valores.',media:'Carpeta multimedia del NAS (MEDIA_ROOT)',value:'Valor obligatorio',enter:'Introducir valor',apply:'Aplicar valor',empty:'Introduzca primero {name}.',path:'MEDIA_ROOT debe ser una carpeta absoluta existente en el NAS.'}
};
function showRequiredComposeFields(){
 const tr=requiredText[lang]||requiredText.de;
 const editor=$('#sourceYaml');let panel=$('#requiredComposeFields');
 // Also work if the user has not yet replaced an older index.html.
 if(!panel){panel=document.createElement('section');panel.id='requiredComposeFields';panel.className='port-review';panel.setAttribute('aria-live','polite');$('#profileReview').insertAdjacentElement('beforebegin',panel)}
 panel.replaceChildren();
 const required=/\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:\?|\?)([^}]*))\}/g;
 const vars=new Map();for(const match of editor.value.matchAll(required)){
  if(!vars.has(match[1]))vars.set(match[1],match[3]||tr.value);
 }
 panel.hidden=vars.size===0;if(!vars.size)return 0;
 const title=document.createElement('strong');title.textContent=tr.title;panel.appendChild(title);
 const caption=document.createElement('p');caption.className='field-note';caption.textContent=tr.caption;panel.appendChild(caption);
 for(const [variable,hint] of vars){
  const wrap=document.createElement('div');wrap.className='full-field';
  const label=document.createElement('label');label.textContent=variable==='MEDIA_ROOT'?tr.media:variable;
  const input=document.createElement('input');input.spellcheck=false;input.autocomplete='off';input.placeholder=variable==='MEDIA_ROOT'?'/DATA/…/Media':tr.enter;
  label.htmlFor='composeVar'+variable;input.id='composeVar'+variable;
  const info=document.createElement('p');info.className='field-note';info.textContent=hint;
  const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=tr.apply;
  button.onclick=async()=>{
   const value=input.value.trim();
   if(!value){notice(tr.empty.replace('{name}',variable),true);return}
   if(variable==='MEDIA_ROOT'&&(!value.startsWith('/')||value.includes(':')||value.split('/').includes('..')||/[\r\n\x00-\x1f]/.test(value))){notice(tr.path,true);return}
   const token=new RegExp('\\$\\{'+variable+'(?:(?::\\?|\\?)[^}]*)\\}','g');
   editor.value=editor.value.replace(token,()=>value);
   showRequiredComposeFields();await refreshPortScan();
  };
  const actions=document.createElement('div');actions.className='im-field-row';actions.append(input,button);
  if(variable==='MEDIA_ROOT'||variable.endsWith('_PATH')||variable.endsWith('_DIR')){
   const browse=document.createElement('button');browse.type='button';browse.className='secondary';browse.textContent=ct('choose');
   browse.onclick=()=>openFolderPicker(path=>{input.value=path},input.value);actions.appendChild(browse);
  }
  wrap.append(label,actions,info);panel.appendChild(wrap);
 }
 return vars.size;
}
function imRenderAutomation(res){
 const a=res.automation;
 if(!a)return;
 const desc=a.official_catalog?ux('sourceOfficial'):a.verified_publisher_compose?ux('sourceVerified'):ux('sourceDetected');
 const precision=a.metadata_only?ux('sourceMetadata'):ux('sourceConfigCheck');
 const info=[desc,precision];
 const panel=$('#sourceDiagnosis');
 // Existing diagnostic panel is reserved for errors; use nonintrusive notification.
 if(a.metadata_only)notice(info.join(' · '));
}
async function analyzeGitHubRepository(body,generation=wizardGeneration){
 let job;
 try { job=await request('/api/analyze/launch',body); }
 catch(e){
  // Safe compatibility path if a proxy blocks this new endpoint or the
  // backend worker cannot be started. The legacy route still supports URL.
  if(/(?:404|502|503|Hintergrundanalyse|not found)/i.test(String(e.message)))
   return request('/api/analyze',body);
  throw e;
 }
 if(!job.job_id)throw Error(ux('scanStartFailed'));
 const deadline=Date.now()+180000;
 while(Date.now()<deadline){
  if(generation!==wizardGeneration)return null;
  await new Promise(resolve=>setTimeout(resolve,1200));
  if(generation!==wizardGeneration)return null;
  let state;
  try {state=await request('/api/analyze/job/'+encodeURIComponent(job.job_id));}
  catch(e){
   // Jobs are in process memory; a proxy or multi-worker setup can route
   // polling to another worker. Fall back once to the existing endpoint.
   if(/(?:404|Analyse nicht mehr verfügbar|Analyse nicht gefunden)/i.test(String(e.message)))
    return request('/api/analyze',body);
   throw e;
  }
  if(state.status==='done'){
   if(!state.result?.source)throw Error(ux('scanNoSource'));
   return state.result;
  }
  if(state.status==='error'){
   const detail=state.error;
   const err=Error(typeof detail==='string'?detail:(detail?.message||JSON.stringify(detail||{})));
   if(detail?.code==='unsupported_source')err.diagnostic=detail;
   throw err;
  }
  if(state.progress)notice(state.progress);
 }
 throw Error(ux('scanTimeout'));
}
function isGitHubRepositorySource(body){
 if(body.kind!=='url')return false;
 try{const u=new URL(body.value);return u.protocol==='https:'&&u.hostname==='github.com'&&u.pathname.split('/').filter(Boolean).length===2}
 catch(e){return false}
}
async function analyze(){const generation=wizardGeneration;planReady=false;showSourceDiagnosis(null);let value=kind==='lsio'?lsioSelected:$('#sourceInput').value.trim();if(!value){notice(t('invalid'),true);return}setBusy(true,$('#analyzeBtn'));try{const body={kind,value,container_port:Number($('#containerPort').value)||null,host_port:Number($('#hostPort').value)||null,config_path:$('#configPath').value.trim()};const res=isGitHubRepositorySource(body)?await analyzeGitHubRepository(body,generation):await request('/api/analyze',body);if(generation!==wizardGeneration)return;setupLaterProfiles.clear();resetProjectIcons();source=res.source;appName=res.name;$('#appName').value=res.name;$('#appTitle').value=res.title;$('#sourceYaml').value=res.source;showRequiredComposeFields();await refreshSettings();if(generation!==wizardGeneration)return;const found=$('#resolvedSource');found.hidden=!res.resolved_url;found.textContent=res.resolved_url?`${(kind==='lsio'||res.resolved_url.toLowerCase().split('?')[0].endsWith('.md')) ? ux('scanSourceDocumentation') : t('resolvedCompose')}: ${res.resolved_url}`:'';$('#dataDir').value=`/DATA/AppData/${res.name}`;$('#iconUrl').value=res.icon_url||'';$('#category').value=(kind==='lsio'&&lsioImages?.find(x=>x.name===lsioSelected)?.category&&[...$('#category').options].some(o=>o.value===lsioImages.find(x=>x.name===lsioSelected).category))?lsioImages.find(x=>x.name===lsioSelected).category:'Others';showPublisherSuggestions(res.image_suggestions||[]);drawProfiles(res.optional_profiles);const project=$('#projectSource');project.hidden=!res.project_url;if(res.project_url){$('#projectLink').textContent=res.project_url;$('#projectLink').href=res.project_url;}selectStep(2);renderResources(false);loadHostResources();loadTimezone(true);imRenderAutomation(res);iconSearchTerms=Array.isArray(res.icon_search_terms)?res.icon_search_terms:[res.name];searchProjectIcons(res.project_url||'');await refreshPortScan();if(generation!==wizardGeneration)return;if(res.notes.length)notice(res.notes.join(' · '))}catch(e){if(generation!==wizardGeneration)return;if(e.diagnostic){showSourceDiagnosis(e.diagnostic);notice('')}else notice(errorMessage(e),true)}finally{if(generation===wizardGeneration)setBusy(false);}}
function jumpToRequirement(kind){
 selectStep(2);
 const target=kind==='cloudflare_auth'?'#cloudflareTunnelToken':kind==='tailscale_auth'?'#tailscaleAuthKey':'#sourceYaml';
 const el=$(target);
 if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.focus({preventScroll:true})}
}
async function choosePublisherFromPreview(item,button){
 if(!item||button.disabled)return;
 button.disabled=true;
 try{
  const result=await request('/api/source/image',{source:$('#sourceYaml').value,service:item.service,expected_image:item.current,replacement_image:item.recommended});
  $('#sourceYaml').value=result.source;showRequiredComposeFields();
  publisherImages=publisherImages.filter(v=>!(v.service===item.service&&v.current===item.current));
  showPublisherSuggestions(publisherImages);
  await refreshPortScan();
  await preview();
 }catch(e){notice(errorMessage(e),true);button.disabled=false}
}
function renderRequirements(messages,actions){
 const wrap=$('#setupIssues');wrap.replaceChildren();
 if(!messages.length)return;
 const hint=document.createElement('p');hint.className='requirement-hint';hint.textContent=ta('actionsHint');wrap.appendChild(hint);
 messages.forEach((message,i)=>{
  const action=(Array.isArray(actions)&&actions[i])||{kind:'source_compose',service:''};
  const entry=document.createElement('div');entry.className='requirement-entry';
  const text=document.createElement('p');text.textContent=message;entry.appendChild(text);
  const btn=document.createElement('button');btn.type='button';btn.className='secondary requirement-action';
  const suggestion=action.kind==='source_image'?publisherImages.find(item=>item.service===action.service):null;
  if(suggestion){
   btn.textContent=ta('usePublisherImage')+' · '+suggestion.recommended;
   btn.onclick=()=>choosePublisherFromPreview(suggestion,btn);
  }else{
   btn.textContent=ta(action.kind==='cloudflare_auth'?'enterCloudflare':action.kind==='tailscale_auth'?'enterTailscale':'editSource');
   btn.onclick=()=>jumpToRequirement(action.kind);
  }
  entry.appendChild(btn);wrap.appendChild(entry);
 });
}
function renderSetupLater(options){
 const box=$('#setupLaterReview');box.replaceChildren();
 if(!Array.isArray(options)||!options.length){box.hidden=true;return}
 box.hidden=false;
 const heading=document.createElement('strong');heading.textContent=st('pendingHeading');box.appendChild(heading);
 const hint=document.createElement('p');hint.className='field-note';hint.textContent=st('pendingDescription');box.appendChild(hint);
 for(const item of options){
  const row=document.createElement('label');row.className='setup-later-entry';
  const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=setupLaterProfiles.has(item.profile);
  checkbox.setAttribute('aria-label',st('label')+': '+item.profile);
  const body=document.createElement('span');
  const title=document.createElement('b');title.textContent=`${item.service} · ${st('label')}`;
  const sub=document.createElement('small');sub.textContent=st('hint');
  body.append(title,sub);row.append(checkbox,body);
  checkbox.addEventListener('change',async()=>{
   if(checkbox.checked)setupLaterProfiles.add(item.profile);else setupLaterProfiles.delete(item.profile);
   await preview();
  });
  box.appendChild(row);
 }
}
async function preview(){
 // Fetch current source credentials even when Compose was edited manually.
 await refreshSettings();
 if(missingSecretsInEditor()){
  selectStep(2);
  const field=$('#composeSettingsPanel').querySelector('.im-credential-missing');
  notice(ct('emptyWarn'),true);
  field?.scrollIntoView({behavior:'smooth',block:'center'});
  field?.querySelector('input')?.focus({preventScroll:true});
  return;
 }
 // Do not send a blocked plan and then show a generic HTTP 400. Point the
 // user at the concrete Compose values that still require an answer.
 if(showRequiredComposeFields()){
  selectStep(2);const panel=$('#requiredComposeFields');
  notice((requiredText[lang]||requiredText.de).caption,true);
  panel.scrollIntoView({behavior:'smooth',block:'center'});
  const first=panel.querySelector('input');if(first)first.focus({preventScroll:true});
  return;
 }
 planReady=false;setBusy(true,$('#previewBtn'));try{const res=await request('/api/preview',{source:$('#sourceYaml').value,name:$('#appName').value,title:$('#appTitle').value,data_dir:$('#dataDir').value,icon:$('#iconUrl').value,category:$('#category').value,selected_profiles:chosenProfiles(),setup_later_profiles:[...setupLaterProfiles],tailscale_auth_key:$('#tailscaleAuthKey').value.trim(),cloudflare_tunnel_token:$('#cloudflareTunnelToken').value.trim(),resources:configuredResources(),...configuredTimezone(),target_system:$('#imTargetSystem').value});$('#generatedCompose').value=res.compose;appName=$('#appName').value;$('#previewInfo').textContent=`${appName} · ${res.services.length} service(s) · ${res.main} · Port ${res.port||'—'}`;planReady=!!res.install_ready;$('#proceedBtn').disabled=!planReady;
  $('#buildConsent').hidden=!res.compose.includes('build:');$('#confirmBuild').checked=false;const readiness=$('#readinessPanel'),heading=$('#readinessHeading'),fixBtn=$('#fixSetupBtn');
  const blockers=Array.isArray(res.setup_issues)?res.setup_issues:[];
  readiness.classList.toggle('blocked',!planReady);heading.textContent=t(planReady?'readinessReady':'readinessBlocked');
  renderRequirements(blockers,res.setup_actions);
  renderSetupLater(res.setup_later_options);
  fixBtn.hidden=planReady;fixBtn.textContent=t('fixSetup');
  const detail=$('#technicalDetails'),summary=$('#technicalSummary'),list=$('#warnings');
  list.replaceChildren();detail.hidden=!res.notes.length;
  summary.textContent=t('technicalSummary')+' ('+res.notes.length+')';
  res.notes.forEach(n=>{const p=document.createElement('p');p.textContent=n;list.appendChild(p)});
  selectStep(3)}catch(e){notice(errorMessage(e),true)}finally{setBusy(false);}}
function downloadCompose(){let b=new Blob([$('#generatedCompose').value],{type:'application/yaml;charset=utf-8'}),url=URL.createObjectURL(b),a=document.createElement('a');a.href=url;a.download=(appName||'zimaos-app')+'.yml';document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url)}
const buildConsentTexts={
 de:'Ich bestätige den lokalen Docker-Build und die Einrichtung einer dauerhaft laufenden Registry nur auf 127.0.0.1:50813, damit ZimaOS die App mit Dashboard-Kachel verwalten kann. Dockerfile-Befehle können Code ausführen; privilegierte Container können auf das NAS zugreifen.',
 en:'I authorize building third-party GitHub source on my NAS and setting up a persistent registry bound only to 127.0.0.1:50813 so ZimaOS can manage the app and dashboard tile. Dockerfiles execute code; privileged containers can access the NAS.',
 fr:'J’autorise la création locale de l’image Docker et un registre persistant limité à 127.0.0.1:50813, pour la gestion de l’application dans ZimaOS. Le Dockerfile exécute du code ; des conteneurs privilégiés peuvent accéder au NAS.',
 pt:'Autorizo a compilação local da imagem Docker e a criação de um registo persistente limitado a 127.0.0.1:50813, para a gestão da aplicação no ZimaOS. O Dockerfile executa código; contentores privilegiados podem aceder ao NAS.',
 es:'Autorizo la compilación local y un registro persistente limitado a 127.0.0.1:50813, para gestionar la aplicación desde ZimaOS. El Dockerfile ejecuta código; los contenedores privilegiados pueden acceder al NAS.'
};
function updateBuildConsentText(){const label=$('#buildConsent span');if(label)label.textContent=buildConsentTexts[lang]||buildConsentTexts.de}
const liveLabels={
 de:{title:'Live-Installationsverlauf',events:'Installationsprotokoll',stages:['Compose & Ports prüfen','ZimaOS-Anmeldung','Vorhandene App prüfen','Docker-Image lokal bauen','Datenordner vorbereiten','Installationsauftrag senden','Docker-Images & Container','Containerstart beobachten','Start überprüfen'],pending:'Noch nicht erstellt',later:'Später einrichten',complete:'Installation erfolgreich überprüft',incomplete:'Installation nicht vollständig gestartet',failed:'Installation fehlgeschlagen'},
 en:{title:'Live installation progress',events:'Installation events',stages:['Check Compose & ports','Sign in to ZimaOS','Check existing app','Build Docker image locally','Prepare data folders','Submit installation','Docker images & containers','Monitor container startup','Verify runtime'],pending:'Not created yet',later:'Set up later',complete:'Installation verified',incomplete:'Installation not fully running',failed:'Installation failed'},
 fr:{title:'Progression de l’installation',events:'Journal d’installation',stages:['Vérifier Compose et ports','Connexion à ZimaOS','Vérifier l’application','Construire l’image Docker','Préparer les dossiers','Envoyer l’installation','Images et conteneurs Docker','Surveiller le démarrage','Vérifier le fonctionnement'],pending:'Pas encore créé',later:'Configurer plus tard',complete:'Installation vérifiée',incomplete:'Démarrage incomplet',failed:'Échec de l’installation'},
 pt:{title:'Progresso da instalação',events:'Registo da instalação',stages:['Verificar Compose e portas','Iniciar sessão no ZimaOS','Verificar aplicação existente','Compilar imagem Docker localmente','Preparar pastas','Enviar instalação','Imagens e contentores Docker','Acompanhar o arranque','Verificar funcionamento'],pending:'Ainda não criado',later:'Configurar mais tarde',complete:'Instalação verificada',incomplete:'Arranque incompleto',failed:'Falha na instalação'},
 es:{title:'Progreso de instalación',events:'Registro de instalación',stages:['Comprobar Compose y puertos','Iniciar sesión en ZimaOS','Comprobar la aplicación','Crear imagen Docker localmente','Preparar carpetas','Enviar instalación','Imágenes y contenedores Docker','Supervisar el arranque','Verificar funcionamiento'],pending:'Aún no creado',later:'Configurar más tarde',complete:'Instalación verificada',incomplete:'Inicio incompleto',failed:'Instalación fallida'}
};
const livePhases=['preflight','login','existing','build','directories','submitted','containers','startup','verification'];
let liveStarted=0;
function liveTranslation(){return liveLabels[lang]||liveLabels.de}
function showLiveStatus(job){
 const tr=liveTranslation();const box=$('#installLive');box.hidden=false;$('#installLiveTitle').textContent=tr.title;$('#installEventsTitle').textContent=tr.events;
 const elapsed=Math.max(0,Math.floor((Date.now()-liveStarted)/1000));$('#installElapsed').textContent=String(Math.floor(elapsed/60)).padStart(2,'0')+':'+String(elapsed%60).padStart(2,'0');
 const progress=livePhases.indexOf(job.phase);const steps=$('#installTimeline');steps.replaceChildren();
 livePhases.forEach((phase,i)=>{const row=document.createElement('div');let state=i<progress?'complete':i===progress?'active':'';
  if((job.state==='error'||job.state==='warning')&&i===progress)state='failed';
  if(job.state==='success'&&i<=progress)state='complete';
  row.className='install-stage '+state;const ic=document.createElement('span');ic.className='install-stage-icon';ic.textContent=state==='complete'?'✓':state==='failed'?'!':state==='active'?'◌':'·';
  const label=document.createElement('span');label.className='install-stage-text';label.textContent=tr.stages[i];row.append(ic,label);steps.append(row);
 });
 const entries=$('#installContainers');entries.replaceChildren();const observed=Array.isArray(job.containers)?job.containers:[];
 for(const c of observed){const row=document.createElement('div');row.className='install-container'+(c.state==='running'?' running':c.state==='exited'||c.state==='dead'?' error':'');const title=document.createElement('strong');title.textContent=c.service;const status=document.createElement('em');const stateKey={running:'stateRunning',exited:'stateExited',dead:'stateDead',created:'stateCreated',restarting:'stateRestarting',paused:'statePaused'}[c.state];const healthKey={healthy:'healthHealthy',unhealthy:'healthUnhealthy',starting:'healthStarting'}[c.health];status.textContent=(stateKey?ux(stateKey):c.state)+(c.health?' · '+(healthKey?ux(healthKey):c.health):'')+(c.state==='exited'?' · '+ux('exitCode')+' '+c.exit_code:'');row.append(title,status);entries.append(row)}
 const events=$('#installEvents');events.replaceChildren();for(const evt of (job.events||[])){const row=document.createElement('div');row.className='install-event';row.textContent=evt.at+' · '+evt.message;events.append(row)}
 $('#installResult').hidden=false;$('#installResult').className='install-result'+(job.state==='success'?' success':job.state==='error'||job.state==='warning'?' error':'');
 $('#installResult').textContent=job.message||'';
}
let imProxyHosts=new Set();
let imInstallTotpRequired=false;
async function loadZimaOsTarget(){
 try{
  const config=await request('/api/zimaos/target');
  if(config.host&&!$('#zimaHost').value.trim())$('#zimaHost').value=config.host;
  updateProxyTotp();
 }catch(e){ /* Address remains editable; never expose credentials. */ }
}
async function saveZimaOsTarget(){
 const input=$('#zimaHost'),raw=input.value.trim();
 if(!raw)return;
 const response=await request('/api/zimaos/target',{host:raw});
 // Do not override more recent edits if the response arrives late.
 if(input.value.trim()===raw)input.value=response.host;
 updateProxyTotp();
}
function updateProxyTotp(){
 const raw=$('#zimaHost').value.trim();let hostname='';
 try{hostname=new URL(raw.includes('://')?raw:'http://'+raw).hostname.toLowerCase()}catch(e){}
 // The security factor follows Install Monitor's proxy access policy, not
 // the ZimaOS target address. Checking the latter allowed bypass via NAS IP.
 $('#proxyTotpBox').hidden=!imInstallTotpRequired;
 // An explicit public ZimaOS target still needs its internal API address.
 $('#internalZimaField').hidden=!imProxyHosts.has(hostname);
}
async function proxyHostsRefresh(){
 const list=$('#proxyHostList');if(!list)return;
 try{
  const info=await request('/api/totp/status');list.replaceChildren();
  if(!info.proxy_hosts.length){list.textContent=ux('proxyNoHosts');return}
  for(const host of info.proxy_hosts){
   const row=document.createElement('div');row.className='im-field-row';row.style.marginTop='7px';
   const name=document.createElement('span');name.style.flex='1';name.textContent=host;
   const remove=document.createElement('button');remove.type='button';remove.className='secondary';remove.textContent=ux('proxyRemove');
   remove.onclick=()=>proxyHostChange(host,true);row.append(name,remove);list.append(row);
  }
 }catch(e){list.textContent=errorMessage(e)}
}
async function proxyHostChange(host,remove){
 const code=$('#proxyHostCode').value.trim();
 if(!/^[0-9]{6}$/.test(code)){notice(ux('proxyCodeRequired'),true);return}
 if(!remove&&!/^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]*$/.test(host)){notice(ux('proxyHostInvalid'),true);return}
 try{await request('/api/proxy/hosts/'+(remove?'remove':'add'),{host,totp_code:code});
  $('#proxyHostCode').value='';$('#proxyHostName').value='';await proxyHostsRefresh();await setupAuthenticatorStatus();notice(ux('proxyHostsUpdated'));
 }catch(e){$('#proxyHostCode').value='';notice(errorMessage(e),true)}
}
async function setupAuthenticatorStatus(){
 try{const s=await request('/api/totp/status');
 imProxyHosts=new Set(s.proxy_hosts||[]);
 imInstallTotpRequired=!!s.requires_install_totp;
 updateProxyTotp();
 $('#authenticatorStatus').textContent=s.enabled?ux('authEnabled')+' '+(s.proxy_hosts.join(', ')||ux('authNone')):ux('authDisabled')+' '+(s.proxy_hosts.join(', ')||ux('authUnset'));
 $('#authenticatorBegin').hidden=s.enabled;
 }catch(e){$('#authenticatorStatus').textContent=errorMessage(e)}
}

// Offline QR renderer, based on Kazuhiko Arase's MIT-licensed QRCode for JavaScript.
// Included locally: TOTP setup keys are never sent to an external QR service.
const imQrLibrary=(()=>{
 const sources={"QR8bitByte":function(require,module,exports){
var QRMode = require('./QRMode');

function QR8bitByte(data) {
	this.mode = QRMode.MODE_8BIT_BYTE;
	this.data = data;
}

QR8bitByte.prototype = {

	getLength : function() {
		return this.data.length;
	},
	
	write : function(buffer) {
		for (var i = 0; i < this.data.length; i++) {
			// not JIS ...
			buffer.put(this.data.charCodeAt(i), 8);
		}
	}
};

module.exports = QR8bitByte;

},
"QRBitBuffer":function(require,module,exports){
function QRBitBuffer() {
	this.buffer = [];
	this.length = 0;
}

QRBitBuffer.prototype = {

	get : function(index) {
		var bufIndex = Math.floor(index / 8);
		return ( (this.buffer[bufIndex] >>> (7 - index % 8) ) & 1) == 1;
	},
	
	put : function(num, length) {
		for (var i = 0; i < length; i++) {
			this.putBit( ( (num >>> (length - i - 1) ) & 1) == 1);
		}
	},
	
	getLengthInBits : function() {
		return this.length;
	},
	
	putBit : function(bit) {
	
		var bufIndex = Math.floor(this.length / 8);
		if (this.buffer.length <= bufIndex) {
			this.buffer.push(0);
		}
	
		if (bit) {
			this.buffer[bufIndex] |= (0x80 >>> (this.length % 8) );
		}
	
		this.length++;
	}
};

module.exports = QRBitBuffer;

},
"QRErrorCorrectLevel":function(require,module,exports){
module.exports = {
	L : 1,
	M : 0,
	Q : 3,
	H : 2
};


},
"QRMaskPattern":function(require,module,exports){
module.exports = {
	PATTERN000 : 0,
	PATTERN001 : 1,
	PATTERN010 : 2,
	PATTERN011 : 3,
	PATTERN100 : 4,
	PATTERN101 : 5,
	PATTERN110 : 6,
	PATTERN111 : 7
};

},
"QRMath":function(require,module,exports){
var QRMath = {

	glog : function(n) {
	
		if (n < 1) {
			throw new Error("glog(" + n + ")");
		}
		
		return QRMath.LOG_TABLE[n];
	},
	
	gexp : function(n) {
	
		while (n < 0) {
			n += 255;
		}
	
		while (n >= 256) {
			n -= 255;
		}
	
		return QRMath.EXP_TABLE[n];
	},
	
	EXP_TABLE : new Array(256),
	
	LOG_TABLE : new Array(256)

};
	
for (var i = 0; i < 8; i++) {
	QRMath.EXP_TABLE[i] = 1 << i;
}
for (var i = 8; i < 256; i++) {
	QRMath.EXP_TABLE[i] = QRMath.EXP_TABLE[i - 4]
		^ QRMath.EXP_TABLE[i - 5]
		^ QRMath.EXP_TABLE[i - 6]
		^ QRMath.EXP_TABLE[i - 8];
}
for (var i = 0; i < 255; i++) {
	QRMath.LOG_TABLE[QRMath.EXP_TABLE[i] ] = i;
}

module.exports = QRMath;

},
"QRMode":function(require,module,exports){
module.exports = {
    MODE_NUMBER :       1 << 0,
    MODE_ALPHA_NUM :    1 << 1,
    MODE_8BIT_BYTE :    1 << 2,
    MODE_KANJI :        1 << 3
};

},
"QRPolynomial":function(require,module,exports){
var QRMath = require('./QRMath');

function QRPolynomial(num, shift) {
	if (num.length === undefined) {
		throw new Error(num.length + "/" + shift);
	}

	var offset = 0;

	while (offset < num.length && num[offset] === 0) {
		offset++;
	}

	this.num = new Array(num.length - offset + shift);
	for (var i = 0; i < num.length - offset; i++) {
		this.num[i] = num[i + offset];
	}
}

QRPolynomial.prototype = {

	get : function(index) {
		return this.num[index];
	},
	
	getLength : function() {
		return this.num.length;
	},
	
	multiply : function(e) {
	
		var num = new Array(this.getLength() + e.getLength() - 1);
	
		for (var i = 0; i < this.getLength(); i++) {
			for (var j = 0; j < e.getLength(); j++) {
				num[i + j] ^= QRMath.gexp(QRMath.glog(this.get(i) ) + QRMath.glog(e.get(j) ) );
			}
		}
	
		return new QRPolynomial(num, 0);
	},
	
	mod : function(e) {
	
		if (this.getLength() - e.getLength() < 0) {
			return this;
		}
	
		var ratio = QRMath.glog(this.get(0) ) - QRMath.glog(e.get(0) );
	
		var num = new Array(this.getLength() );
		
		for (var i = 0; i < this.getLength(); i++) {
			num[i] = this.get(i);
		}
		
		for (var x = 0; x < e.getLength(); x++) {
			num[x] ^= QRMath.gexp(QRMath.glog(e.get(x) ) + ratio);
		}
	
		// recursive call
		return new QRPolynomial(num, 0).mod(e);
	}
};

module.exports = QRPolynomial;

},
"QRRSBlock":function(require,module,exports){
var QRErrorCorrectLevel = require('./QRErrorCorrectLevel');

function QRRSBlock(totalCount, dataCount) {
	this.totalCount = totalCount;
	this.dataCount  = dataCount;
}

QRRSBlock.RS_BLOCK_TABLE = [

	// L
	// M
	// Q
	// H

	// 1
	[1, 26, 19],
	[1, 26, 16],
	[1, 26, 13],
	[1, 26, 9],
	
	// 2
	[1, 44, 34],
	[1, 44, 28],
	[1, 44, 22],
	[1, 44, 16],

	// 3
	[1, 70, 55],
	[1, 70, 44],
	[2, 35, 17],
	[2, 35, 13],

	// 4		
	[1, 100, 80],
	[2, 50, 32],
	[2, 50, 24],
	[4, 25, 9],
	
	// 5
	[1, 134, 108],
	[2, 67, 43],
	[2, 33, 15, 2, 34, 16],
	[2, 33, 11, 2, 34, 12],
	
	// 6
	[2, 86, 68],
	[4, 43, 27],
	[4, 43, 19],
	[4, 43, 15],
	
	// 7		
	[2, 98, 78],
	[4, 49, 31],
	[2, 32, 14, 4, 33, 15],
	[4, 39, 13, 1, 40, 14],
	
	// 8
	[2, 121, 97],
	[2, 60, 38, 2, 61, 39],
	[4, 40, 18, 2, 41, 19],
	[4, 40, 14, 2, 41, 15],
	
	// 9
	[2, 146, 116],
	[3, 58, 36, 2, 59, 37],
	[4, 36, 16, 4, 37, 17],
	[4, 36, 12, 4, 37, 13],
	
	// 10		
	[2, 86, 68, 2, 87, 69],
	[4, 69, 43, 1, 70, 44],
	[6, 43, 19, 2, 44, 20],
	[6, 43, 15, 2, 44, 16],

	// 11
	[4, 101, 81],
	[1, 80, 50, 4, 81, 51],
	[4, 50, 22, 4, 51, 23],
	[3, 36, 12, 8, 37, 13],

	// 12
	[2, 116, 92, 2, 117, 93],
	[6, 58, 36, 2, 59, 37],
	[4, 46, 20, 6, 47, 21],
	[7, 42, 14, 4, 43, 15],

	// 13
	[4, 133, 107],
	[8, 59, 37, 1, 60, 38],
	[8, 44, 20, 4, 45, 21],
	[12, 33, 11, 4, 34, 12],

	// 14
	[3, 145, 115, 1, 146, 116],
	[4, 64, 40, 5, 65, 41],
	[11, 36, 16, 5, 37, 17],
	[11, 36, 12, 5, 37, 13],

	// 15
	[5, 109, 87, 1, 110, 88],
	[5, 65, 41, 5, 66, 42],
	[5, 54, 24, 7, 55, 25],
	[11, 36, 12],

	// 16
	[5, 122, 98, 1, 123, 99],
	[7, 73, 45, 3, 74, 46],
	[15, 43, 19, 2, 44, 20],
	[3, 45, 15, 13, 46, 16],

	// 17
	[1, 135, 107, 5, 136, 108],
	[10, 74, 46, 1, 75, 47],
	[1, 50, 22, 15, 51, 23],
	[2, 42, 14, 17, 43, 15],

	// 18
	[5, 150, 120, 1, 151, 121],
	[9, 69, 43, 4, 70, 44],
	[17, 50, 22, 1, 51, 23],
	[2, 42, 14, 19, 43, 15],

	// 19
	[3, 141, 113, 4, 142, 114],
	[3, 70, 44, 11, 71, 45],
	[17, 47, 21, 4, 48, 22],
	[9, 39, 13, 16, 40, 14],

	// 20
	[3, 135, 107, 5, 136, 108],
	[3, 67, 41, 13, 68, 42],
	[15, 54, 24, 5, 55, 25],
	[15, 43, 15, 10, 44, 16],

	// 21
	[4, 144, 116, 4, 145, 117],
	[17, 68, 42],
	[17, 50, 22, 6, 51, 23],
	[19, 46, 16, 6, 47, 17],

	// 22
	[2, 139, 111, 7, 140, 112],
	[17, 74, 46],
	[7, 54, 24, 16, 55, 25],
	[34, 37, 13],

	// 23
	[4, 151, 121, 5, 152, 122],
	[4, 75, 47, 14, 76, 48],
	[11, 54, 24, 14, 55, 25],
	[16, 45, 15, 14, 46, 16],

	// 24
	[6, 147, 117, 4, 148, 118],
	[6, 73, 45, 14, 74, 46],
	[11, 54, 24, 16, 55, 25],
	[30, 46, 16, 2, 47, 17],

	// 25
	[8, 132, 106, 4, 133, 107],
	[8, 75, 47, 13, 76, 48],
	[7, 54, 24, 22, 55, 25],
	[22, 45, 15, 13, 46, 16],

	// 26
	[10, 142, 114, 2, 143, 115],
	[19, 74, 46, 4, 75, 47],
	[28, 50, 22, 6, 51, 23],
	[33, 46, 16, 4, 47, 17],

	// 27
	[8, 152, 122, 4, 153, 123],
	[22, 73, 45, 3, 74, 46],
	[8, 53, 23, 26, 54, 24],
	[12, 45, 15, 28, 46, 16],

	// 28
	[3, 147, 117, 10, 148, 118],
	[3, 73, 45, 23, 74, 46],
	[4, 54, 24, 31, 55, 25],
	[11, 45, 15, 31, 46, 16],

	// 29
	[7, 146, 116, 7, 147, 117],
	[21, 73, 45, 7, 74, 46],
	[1, 53, 23, 37, 54, 24],
	[19, 45, 15, 26, 46, 16],

	// 30
	[5, 145, 115, 10, 146, 116],
	[19, 75, 47, 10, 76, 48],
	[15, 54, 24, 25, 55, 25],
	[23, 45, 15, 25, 46, 16],

	// 31
	[13, 145, 115, 3, 146, 116],
	[2, 74, 46, 29, 75, 47],
	[42, 54, 24, 1, 55, 25],
	[23, 45, 15, 28, 46, 16],

	// 32
	[17, 145, 115],
	[10, 74, 46, 23, 75, 47],
	[10, 54, 24, 35, 55, 25],
	[19, 45, 15, 35, 46, 16],

	// 33
	[17, 145, 115, 1, 146, 116],
	[14, 74, 46, 21, 75, 47],
	[29, 54, 24, 19, 55, 25],
	[11, 45, 15, 46, 46, 16],

	// 34
	[13, 145, 115, 6, 146, 116],
	[14, 74, 46, 23, 75, 47],
	[44, 54, 24, 7, 55, 25],
	[59, 46, 16, 1, 47, 17],

	// 35
	[12, 151, 121, 7, 152, 122],
	[12, 75, 47, 26, 76, 48],
	[39, 54, 24, 14, 55, 25],
	[22, 45, 15, 41, 46, 16],

	// 36
	[6, 151, 121, 14, 152, 122],
	[6, 75, 47, 34, 76, 48],
	[46, 54, 24, 10, 55, 25],
	[2, 45, 15, 64, 46, 16],

	// 37
	[17, 152, 122, 4, 153, 123],
	[29, 74, 46, 14, 75, 47],
	[49, 54, 24, 10, 55, 25],
	[24, 45, 15, 46, 46, 16],

	// 38
	[4, 152, 122, 18, 153, 123],
	[13, 74, 46, 32, 75, 47],
	[48, 54, 24, 14, 55, 25],
	[42, 45, 15, 32, 46, 16],

	// 39
	[20, 147, 117, 4, 148, 118],
	[40, 75, 47, 7, 76, 48],
	[43, 54, 24, 22, 55, 25],
	[10, 45, 15, 67, 46, 16],

	// 40
	[19, 148, 118, 6, 149, 119],
	[18, 75, 47, 31, 76, 48],
	[34, 54, 24, 34, 55, 25],
	[20, 45, 15, 61, 46, 16]
];

QRRSBlock.getRSBlocks = function(typeNumber, errorCorrectLevel) {
	
	var rsBlock = QRRSBlock.getRsBlockTable(typeNumber, errorCorrectLevel);
	
	if (rsBlock === undefined) {
		throw new Error("bad rs block @ typeNumber:" + typeNumber + "/errorCorrectLevel:" + errorCorrectLevel);
	}

	var length = rsBlock.length / 3;
	
	var list = [];
	
	for (var i = 0; i < length; i++) {

		var count = rsBlock[i * 3 + 0];
		var totalCount = rsBlock[i * 3 + 1];
		var dataCount  = rsBlock[i * 3 + 2];

		for (var j = 0; j < count; j++) {
			list.push(new QRRSBlock(totalCount, dataCount) );	
		}
	}
	
	return list;
};

QRRSBlock.getRsBlockTable = function(typeNumber, errorCorrectLevel) {

	switch(errorCorrectLevel) {
	case QRErrorCorrectLevel.L :
		return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 0];
	case QRErrorCorrectLevel.M :
		return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 1];
	case QRErrorCorrectLevel.Q :
		return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 2];
	case QRErrorCorrectLevel.H :
		return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 3];
	default :
		return undefined;
	}
};

module.exports = QRRSBlock;

},
"QRUtil":function(require,module,exports){
var QRMode = require('./QRMode');
var QRPolynomial = require('./QRPolynomial');
var QRMath = require('./QRMath');
var QRMaskPattern = require('./QRMaskPattern');

var QRUtil = {

    PATTERN_POSITION_TABLE : [
        [],
        [6, 18],
        [6, 22],
        [6, 26],
        [6, 30],
        [6, 34],
        [6, 22, 38],
        [6, 24, 42],
        [6, 26, 46],
        [6, 28, 50],
        [6, 30, 54],        
        [6, 32, 58],
        [6, 34, 62],
        [6, 26, 46, 66],
        [6, 26, 48, 70],
        [6, 26, 50, 74],
        [6, 30, 54, 78],
        [6, 30, 56, 82],
        [6, 30, 58, 86],
        [6, 34, 62, 90],
        [6, 28, 50, 72, 94],
        [6, 26, 50, 74, 98],
        [6, 30, 54, 78, 102],
        [6, 28, 54, 80, 106],
        [6, 32, 58, 84, 110],
        [6, 30, 58, 86, 114],
        [6, 34, 62, 90, 118],
        [6, 26, 50, 74, 98, 122],
        [6, 30, 54, 78, 102, 126],
        [6, 26, 52, 78, 104, 130],
        [6, 30, 56, 82, 108, 134],
        [6, 34, 60, 86, 112, 138],
        [6, 30, 58, 86, 114, 142],
        [6, 34, 62, 90, 118, 146],
        [6, 30, 54, 78, 102, 126, 150],
        [6, 24, 50, 76, 102, 128, 154],
        [6, 28, 54, 80, 106, 132, 158],
        [6, 32, 58, 84, 110, 136, 162],
        [6, 26, 54, 82, 110, 138, 166],
        [6, 30, 58, 86, 114, 142, 170]
    ],

    G15 : (1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 2) | (1 << 1) | (1 << 0),
    G18 : (1 << 12) | (1 << 11) | (1 << 10) | (1 << 9) | (1 << 8) | (1 << 5) | (1 << 2) | (1 << 0),
    G15_MASK : (1 << 14) | (1 << 12) | (1 << 10)    | (1 << 4) | (1 << 1),

    getBCHTypeInfo : function(data) {
        var d = data << 10;
        while (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G15) >= 0) {
            d ^= (QRUtil.G15 << (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G15) ) );    
        }
        return ( (data << 10) | d) ^ QRUtil.G15_MASK;
    },

    getBCHTypeNumber : function(data) {
        var d = data << 12;
        while (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G18) >= 0) {
            d ^= (QRUtil.G18 << (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G18) ) );    
        }
        return (data << 12) | d;
    },

    getBCHDigit : function(data) {

        var digit = 0;

        while (data !== 0) {
            digit++;
            data >>>= 1;
        }

        return digit;
    },

    getPatternPosition : function(typeNumber) {
        return QRUtil.PATTERN_POSITION_TABLE[typeNumber - 1];
    },

    getMask : function(maskPattern, i, j) {
        
        switch (maskPattern) {
            
        case QRMaskPattern.PATTERN000 : return (i + j) % 2 === 0;
        case QRMaskPattern.PATTERN001 : return i % 2 === 0;
        case QRMaskPattern.PATTERN010 : return j % 3 === 0;
        case QRMaskPattern.PATTERN011 : return (i + j) % 3 === 0;
        case QRMaskPattern.PATTERN100 : return (Math.floor(i / 2) + Math.floor(j / 3) ) % 2 === 0;
        case QRMaskPattern.PATTERN101 : return (i * j) % 2 + (i * j) % 3 === 0;
        case QRMaskPattern.PATTERN110 : return ( (i * j) % 2 + (i * j) % 3) % 2 === 0;
        case QRMaskPattern.PATTERN111 : return ( (i * j) % 3 + (i + j) % 2) % 2 === 0;

        default :
            throw new Error("bad maskPattern:" + maskPattern);
        }
    },

    getErrorCorrectPolynomial : function(errorCorrectLength) {

        var a = new QRPolynomial([1], 0);

        for (var i = 0; i < errorCorrectLength; i++) {
            a = a.multiply(new QRPolynomial([1, QRMath.gexp(i)], 0) );
        }

        return a;
    },

    getLengthInBits : function(mode, type) {

        if (1 <= type && type < 10) {

            // 1 - 9

            switch(mode) {
            case QRMode.MODE_NUMBER     : return 10;
            case QRMode.MODE_ALPHA_NUM  : return 9;
            case QRMode.MODE_8BIT_BYTE  : return 8;
            case QRMode.MODE_KANJI      : return 8;
            default :
                throw new Error("mode:" + mode);
            }

        } else if (type < 27) {

            // 10 - 26

            switch(mode) {
            case QRMode.MODE_NUMBER     : return 12;
            case QRMode.MODE_ALPHA_NUM  : return 11;
            case QRMode.MODE_8BIT_BYTE  : return 16;
            case QRMode.MODE_KANJI      : return 10;
            default :
                throw new Error("mode:" + mode);
            }

        } else if (type < 41) {

            // 27 - 40

            switch(mode) {
            case QRMode.MODE_NUMBER     : return 14;
            case QRMode.MODE_ALPHA_NUM  : return 13;
            case QRMode.MODE_8BIT_BYTE  : return 16;
            case QRMode.MODE_KANJI      : return 12;
            default :
                throw new Error("mode:" + mode);
            }

        } else {
            throw new Error("type:" + type);
        }
    },

    getLostPoint : function(qrCode) {
        
        var moduleCount = qrCode.getModuleCount();
        var lostPoint = 0;
        var row = 0; 
        var col = 0;

        
        // LEVEL1
        
        for (row = 0; row < moduleCount; row++) {

            for (col = 0; col < moduleCount; col++) {

                var sameCount = 0;
                var dark = qrCode.isDark(row, col);

                for (var r = -1; r <= 1; r++) {

                    if (row + r < 0 || moduleCount <= row + r) {
                        continue;
                    }

                    for (var c = -1; c <= 1; c++) {

                        if (col + c < 0 || moduleCount <= col + c) {
                            continue;
                        }

                        if (r === 0 && c === 0) {
                            continue;
                        }

                        if (dark === qrCode.isDark(row + r, col + c) ) {
                            sameCount++;
                        }
                    }
                }

                if (sameCount > 5) {
                    lostPoint += (3 + sameCount - 5);
                }
            }
        }

        // LEVEL2

        for (row = 0; row < moduleCount - 1; row++) {
            for (col = 0; col < moduleCount - 1; col++) {
                var count = 0;
                if (qrCode.isDark(row,     col    ) ) count++;
                if (qrCode.isDark(row + 1, col    ) ) count++;
                if (qrCode.isDark(row,     col + 1) ) count++;
                if (qrCode.isDark(row + 1, col + 1) ) count++;
                if (count === 0 || count === 4) {
                    lostPoint += 3;
                }
            }
        }

        // LEVEL3

        for (row = 0; row < moduleCount; row++) {
            for (col = 0; col < moduleCount - 6; col++) {
                if (qrCode.isDark(row, col) && 
                        !qrCode.isDark(row, col + 1) && 
                         qrCode.isDark(row, col + 2) && 
                         qrCode.isDark(row, col + 3) && 
                         qrCode.isDark(row, col + 4) && 
                        !qrCode.isDark(row, col + 5) && 
                         qrCode.isDark(row, col + 6) ) {
                    lostPoint += 40;
                }
            }
        }

        for (col = 0; col < moduleCount; col++) {
            for (row = 0; row < moduleCount - 6; row++) {
                if (qrCode.isDark(row, col) &&
                        !qrCode.isDark(row + 1, col) &&
                         qrCode.isDark(row + 2, col) &&
                         qrCode.isDark(row + 3, col) &&
                         qrCode.isDark(row + 4, col) &&
                        !qrCode.isDark(row + 5, col) &&
                         qrCode.isDark(row + 6, col) ) {
                    lostPoint += 40;
                }
            }
        }

        // LEVEL4
        
        var darkCount = 0;

        for (col = 0; col < moduleCount; col++) {
            for (row = 0; row < moduleCount; row++) {
                if (qrCode.isDark(row, col) ) {
                    darkCount++;
                }
            }
        }
        
        var ratio = Math.abs(100 * darkCount / moduleCount / moduleCount - 50) / 5;
        lostPoint += ratio * 10;

        return lostPoint;       
    }

};

module.exports = QRUtil;

},
"index":function(require,module,exports){
//---------------------------------------------------------------------
// QRCode for JavaScript
//
// Copyright (c) 2009 Kazuhiko Arase
//
// URL: http://www.d-project.com/
//
// Licensed under the MIT license:
//   http://www.opensource.org/licenses/mit-license.php
//
// The word "QR Code" is registered trademark of 
// DENSO WAVE INCORPORATED
//   http://www.denso-wave.com/qrcode/faqpatent-e.html
//
//---------------------------------------------------------------------
// Modified to work in node for this project (and some refactoring)
//---------------------------------------------------------------------

var QR8bitByte = require('./QR8bitByte');
var QRUtil = require('./QRUtil');
var QRPolynomial = require('./QRPolynomial');
var QRRSBlock = require('./QRRSBlock');
var QRBitBuffer = require('./QRBitBuffer');

function QRCode(typeNumber, errorCorrectLevel) {
	this.typeNumber = typeNumber;
	this.errorCorrectLevel = errorCorrectLevel;
	this.modules = null;
	this.moduleCount = 0;
	this.dataCache = null;
	this.dataList = [];
}

QRCode.prototype = {
	
	addData : function(data) {
		var newData = new QR8bitByte(data);
		this.dataList.push(newData);
		this.dataCache = null;
	},
	
	isDark : function(row, col) {
		if (row < 0 || this.moduleCount <= row || col < 0 || this.moduleCount <= col) {
			throw new Error(row + "," + col);
		}
		return this.modules[row][col];
	},

	getModuleCount : function() {
		return this.moduleCount;
	},
	
	make : function() {
		// Calculate automatically typeNumber if provided is < 1
		if (this.typeNumber < 1 ){
			var typeNumber = 1;
			for (typeNumber = 1; typeNumber < 40; typeNumber++) {
				var rsBlocks = QRRSBlock.getRSBlocks(typeNumber, this.errorCorrectLevel);

				var buffer = new QRBitBuffer();
				var totalDataCount = 0;
				for (var i = 0; i < rsBlocks.length; i++) {
					totalDataCount += rsBlocks[i].dataCount;
				}

				for (var x = 0; x < this.dataList.length; x++) {
					var data = this.dataList[x];
					buffer.put(data.mode, 4);
					buffer.put(data.getLength(), QRUtil.getLengthInBits(data.mode, typeNumber) );
					data.write(buffer);
				}
				if (buffer.getLengthInBits() <= totalDataCount * 8)
					break;
			}
			this.typeNumber = typeNumber;
		}
		this.makeImpl(false, this.getBestMaskPattern() );
	},
	
	makeImpl : function(test, maskPattern) {
		
		this.moduleCount = this.typeNumber * 4 + 17;
		this.modules = new Array(this.moduleCount);
		
		for (var row = 0; row < this.moduleCount; row++) {
			
			this.modules[row] = new Array(this.moduleCount);
			
			for (var col = 0; col < this.moduleCount; col++) {
				this.modules[row][col] = null;//(col + row) % 3;
			}
		}
	
		this.setupPositionProbePattern(0, 0);
		this.setupPositionProbePattern(this.moduleCount - 7, 0);
		this.setupPositionProbePattern(0, this.moduleCount - 7);
		this.setupPositionAdjustPattern();
		this.setupTimingPattern();
		this.setupTypeInfo(test, maskPattern);
		
		if (this.typeNumber >= 7) {
			this.setupTypeNumber(test);
		}
	
		if (this.dataCache === null) {
			this.dataCache = QRCode.createData(this.typeNumber, this.errorCorrectLevel, this.dataList);
		}
	
		this.mapData(this.dataCache, maskPattern);
	},

	setupPositionProbePattern : function(row, col)  {
		
		for (var r = -1; r <= 7; r++) {
			
			if (row + r <= -1 || this.moduleCount <= row + r) continue;
			
			for (var c = -1; c <= 7; c++) {
				
				if (col + c <= -1 || this.moduleCount <= col + c) continue;
				
				if ( (0 <= r && r <= 6 && (c === 0 || c === 6) ) || 
                     (0 <= c && c <= 6 && (r === 0 || r === 6) ) || 
                     (2 <= r && r <= 4 && 2 <= c && c <= 4) ) {
					this.modules[row + r][col + c] = true;
				} else {
					this.modules[row + r][col + c] = false;
				}
			}		
		}		
	},
	
	getBestMaskPattern : function() {
	
		var minLostPoint = 0;
		var pattern = 0;
	
		for (var i = 0; i < 8; i++) {
			
			this.makeImpl(true, i);
	
			var lostPoint = QRUtil.getLostPoint(this);
	
			if (i === 0 || minLostPoint >  lostPoint) {
				minLostPoint = lostPoint;
				pattern = i;
			}
		}
	
		return pattern;
	},
	
	createMovieClip : function(target_mc, instance_name, depth) {
	
		var qr_mc = target_mc.createEmptyMovieClip(instance_name, depth);
		var cs = 1;
	
		this.make();

		for (var row = 0; row < this.modules.length; row++) {
			
			var y = row * cs;
			
			for (var col = 0; col < this.modules[row].length; col++) {
	
				var x = col * cs;
				var dark = this.modules[row][col];
			
				if (dark) {
					qr_mc.beginFill(0, 100);
					qr_mc.moveTo(x, y);
					qr_mc.lineTo(x + cs, y);
					qr_mc.lineTo(x + cs, y + cs);
					qr_mc.lineTo(x, y + cs);
					qr_mc.endFill();
				}
			}
		}
		
		return qr_mc;
	},

	setupTimingPattern : function() {
		
		for (var r = 8; r < this.moduleCount - 8; r++) {
			if (this.modules[r][6] !== null) {
				continue;
			}
			this.modules[r][6] = (r % 2 === 0);
		}
	
		for (var c = 8; c < this.moduleCount - 8; c++) {
			if (this.modules[6][c] !== null) {
				continue;
			}
			this.modules[6][c] = (c % 2 === 0);
		}
	},
	
	setupPositionAdjustPattern : function() {
	
		var pos = QRUtil.getPatternPosition(this.typeNumber);
		
		for (var i = 0; i < pos.length; i++) {
		
			for (var j = 0; j < pos.length; j++) {
			
				var row = pos[i];
				var col = pos[j];
				
				if (this.modules[row][col] !== null) {
					continue;
				}
				
				for (var r = -2; r <= 2; r++) {
				
					for (var c = -2; c <= 2; c++) {
					
						if (Math.abs(r) === 2 || 
                            Math.abs(c) === 2 ||
                            (r === 0 && c === 0) ) {
							this.modules[row + r][col + c] = true;
						} else {
							this.modules[row + r][col + c] = false;
						}
					}
				}
			}
		}
	},
	
	setupTypeNumber : function(test) {
	
		var bits = QRUtil.getBCHTypeNumber(this.typeNumber);
        var mod;
	
		for (var i = 0; i < 18; i++) {
			mod = (!test && ( (bits >> i) & 1) === 1);
			this.modules[Math.floor(i / 3)][i % 3 + this.moduleCount - 8 - 3] = mod;
		}
	
		for (var x = 0; x < 18; x++) {
			mod = (!test && ( (bits >> x) & 1) === 1);
			this.modules[x % 3 + this.moduleCount - 8 - 3][Math.floor(x / 3)] = mod;
		}
	},
	
	setupTypeInfo : function(test, maskPattern) {
	
		var data = (this.errorCorrectLevel << 3) | maskPattern;
		var bits = QRUtil.getBCHTypeInfo(data);
        var mod;
	
		// vertical		
		for (var v = 0; v < 15; v++) {
	
			mod = (!test && ( (bits >> v) & 1) === 1);
	
			if (v < 6) {
				this.modules[v][8] = mod;
			} else if (v < 8) {
				this.modules[v + 1][8] = mod;
			} else {
				this.modules[this.moduleCount - 15 + v][8] = mod;
			}
		}
	
		// horizontal
		for (var h = 0; h < 15; h++) {
	
			mod = (!test && ( (bits >> h) & 1) === 1);
			
			if (h < 8) {
				this.modules[8][this.moduleCount - h - 1] = mod;
			} else if (h < 9) {
				this.modules[8][15 - h - 1 + 1] = mod;
			} else {
				this.modules[8][15 - h - 1] = mod;
			}
		}
	
		// fixed module
		this.modules[this.moduleCount - 8][8] = (!test);
	
	},
	
	mapData : function(data, maskPattern) {
		
		var inc = -1;
		var row = this.moduleCount - 1;
		var bitIndex = 7;
		var byteIndex = 0;
		
		for (var col = this.moduleCount - 1; col > 0; col -= 2) {
	
			if (col === 6) col--;
	
			while (true) {
	
				for (var c = 0; c < 2; c++) {
					
					if (this.modules[row][col - c] === null) {
						
						var dark = false;
	
						if (byteIndex < data.length) {
							dark = ( ( (data[byteIndex] >>> bitIndex) & 1) === 1);
						}
	
						var mask = QRUtil.getMask(maskPattern, row, col - c);
	
						if (mask) {
							dark = !dark;
						}
						
						this.modules[row][col - c] = dark;
						bitIndex--;
	
						if (bitIndex === -1) {
							byteIndex++;
							bitIndex = 7;
						}
					}
				}
								
				row += inc;
	
				if (row < 0 || this.moduleCount <= row) {
					row -= inc;
					inc = -inc;
					break;
				}
			}
		}
		
	}

};

QRCode.PAD0 = 0xEC;
QRCode.PAD1 = 0x11;

QRCode.createData = function(typeNumber, errorCorrectLevel, dataList) {
	
	var rsBlocks = QRRSBlock.getRSBlocks(typeNumber, errorCorrectLevel);
	
	var buffer = new QRBitBuffer();
	
	for (var i = 0; i < dataList.length; i++) {
		var data = dataList[i];
		buffer.put(data.mode, 4);
		buffer.put(data.getLength(), QRUtil.getLengthInBits(data.mode, typeNumber) );
		data.write(buffer);
	}

	// calc num max data.
	var totalDataCount = 0;
	for (var x = 0; x < rsBlocks.length; x++) {
		totalDataCount += rsBlocks[x].dataCount;
	}

	if (buffer.getLengthInBits() > totalDataCount * 8) {
		throw new Error("code length overflow. (" + 
            buffer.getLengthInBits() + 
            ">" +  
            totalDataCount * 8 + 
            ")");
	}

	// end code
	if (buffer.getLengthInBits() + 4 <= totalDataCount * 8) {
		buffer.put(0, 4);
	}

	// padding
	while (buffer.getLengthInBits() % 8 !== 0) {
		buffer.putBit(false);
	}

	// padding
	while (true) {
		
		if (buffer.getLengthInBits() >= totalDataCount * 8) {
			break;
		}
		buffer.put(QRCode.PAD0, 8);
		
		if (buffer.getLengthInBits() >= totalDataCount * 8) {
			break;
		}
		buffer.put(QRCode.PAD1, 8);
	}

	return QRCode.createBytes(buffer, rsBlocks);
};

QRCode.createBytes = function(buffer, rsBlocks) {

	var offset = 0;
	
	var maxDcCount = 0;
	var maxEcCount = 0;
	
	var dcdata = new Array(rsBlocks.length);
	var ecdata = new Array(rsBlocks.length);
	
	for (var r = 0; r < rsBlocks.length; r++) {

		var dcCount = rsBlocks[r].dataCount;
		var ecCount = rsBlocks[r].totalCount - dcCount;

		maxDcCount = Math.max(maxDcCount, dcCount);
		maxEcCount = Math.max(maxEcCount, ecCount);
		
		dcdata[r] = new Array(dcCount);
		
		for (var i = 0; i < dcdata[r].length; i++) {
			dcdata[r][i] = 0xff & buffer.buffer[i + offset];
		}
		offset += dcCount;
		
		var rsPoly = QRUtil.getErrorCorrectPolynomial(ecCount);
		var rawPoly = new QRPolynomial(dcdata[r], rsPoly.getLength() - 1);

		var modPoly = rawPoly.mod(rsPoly);
		ecdata[r] = new Array(rsPoly.getLength() - 1);
		for (var x = 0; x < ecdata[r].length; x++) {
            var modIndex = x + modPoly.getLength() - ecdata[r].length;
			ecdata[r][x] = (modIndex >= 0)? modPoly.get(modIndex) : 0;
		}

	}
	
	var totalCodeCount = 0;
	for (var y = 0; y < rsBlocks.length; y++) {
		totalCodeCount += rsBlocks[y].totalCount;
	}

	var data = new Array(totalCodeCount);
	var index = 0;

	for (var z = 0; z < maxDcCount; z++) {
		for (var s = 0; s < rsBlocks.length; s++) {
			if (z < dcdata[s].length) {
				data[index++] = dcdata[s][z];
			}
		}
	}

	for (var xx = 0; xx < maxEcCount; xx++) {
		for (var t = 0; t < rsBlocks.length; t++) {
			if (xx < ecdata[t].length) {
				data[index++] = ecdata[t][xx];
			}
		}
	}

	return data;

};

module.exports = QRCode;

}};
 const cache={};
 function load(name){
   name=name.replace(/^\.\//,'');
   if(cache[name])return cache[name].exports;
   if(!Object.prototype.hasOwnProperty.call(sources,name))throw Error('QR module unavailable');
   const module={exports:{}};cache[name]=module;
   sources[name]((child)=>load(child),module,module.exports);
   return module.exports;
 }
 return {QRCode:load('index'),errorLevel:load('QRErrorCorrectLevel')};
})();
function showAuthenticatorQr(uri){
 const target=$('#authenticatorQr');target.replaceChildren();
 if(!uri||!uri.startsWith('otpauth://totp/'))throw Error('Ungültige Authenticator-Einrichtung.');
 const qr=new imQrLibrary.QRCode(0,imQrLibrary.errorLevel.M);
 qr.addData(uri);qr.make();
 const count=qr.getModuleCount(),margin=4,cell=5;
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 svg.setAttribute('viewBox',`0 0 ${count+margin*2} ${count+margin*2}`);
 svg.setAttribute('width',String((count+margin*2)*cell));
 svg.setAttribute('height',String((count+margin*2)*cell));
 svg.setAttribute('role','img');svg.setAttribute('aria-label','Authenticator-QR-Code');
 const backdrop=document.createElementNS('http://www.w3.org/2000/svg','rect');
 backdrop.setAttribute('width','100%');backdrop.setAttribute('height','100%');backdrop.setAttribute('fill','#fff');svg.append(backdrop);
 const path=document.createElementNS('http://www.w3.org/2000/svg','path');
 let d='';for(let y=0;y<count;y++)for(let x=0;x<count;x++)if(qr.isDark(y,x))d+=`M${x+margin} ${y+margin}h1v1h-1z`;
 path.setAttribute('d',d);path.setAttribute('fill','#000');svg.append(path);target.append(svg);
}

async function beginAuthenticator(){
 try{const result=await request('/api/totp/setup',{});showAuthenticatorQr(result.uri);$('#authenticatorSecret').value=result.secret;$('#authenticatorPending').hidden=false;
 }catch(e){notice(errorMessage(e),true)}
}
async function confirmAuthenticator(){
 try{await request('/api/totp/confirm',{code:$('#authenticatorConfirmCode').value.trim()});$('#authenticatorPending').hidden=true;$('#authenticatorSecret').value='';$('#authenticatorConfirmCode').value='';await setupAuthenticatorStatus();
 }catch(e){notice(errorMessage(e),true)}
}
async function install(){
 // Never submit the same successfully verified installation a second time.
 if(installed||busy)return;
 updateProxyTotp();if(!$('#proxyTotpBox').hidden&&!/^[0-9]{6}$/.test($('#installTotpCode').value.trim())){notice(ux('installAuthRequired'),true);return}

 if(!$('#confirmInstall').checked){notice(t('needConfirm'),true);return}
 if(!$('#buildConsent').hidden&&!$('#confirmBuild').checked){notice(ux('installBuildRequired'),true);return}
 setBusy(true,$('#installBtn'));liveStarted=Date.now();$('#installLive').hidden=false;$('#installResult').hidden=true;$('#checkBtn').hidden=true;
 try{
  await saveZimaOsTarget();
  const result=await request('/api/install/start',{compose:$('#generatedCompose').value,host:$('#zimaHost').value.trim(),internal_host:$('#internalZimaHost').value.trim(),username:$('#zimaUser').value.trim(),password:$('#zimaPassword').value,confirmed:true,build_confirmed:!$('#buildConsent').hidden&&$('#confirmBuild').checked,totp_code:$('#installTotpCode').value.trim(),target_system:$('#imTargetSystem').value});
  // The worker already owns the supplied password; it must not be retained in the field.
  $('#zimaPassword').value='';$('#installTotpCode').value='';
  let job={state:'queued',phase:'preflight',message:ux('installPreparing'),events:[],containers:[]},failures=0;
  while(true){
   await new Promise(resolve=>setTimeout(resolve,1500));
   try{job=await request('/api/install/jobs/'+encodeURIComponent(result.job_id));failures=0}
   catch(e){if(++failures<5)continue;throw Error(ux('installInterrupted')+' '+errorMessage(e))}
   showLiveStatus(job);
   if(['success','warning','error'].includes(job.state))break;
  }
  installed=job.state==='success';$('#checkBtn').hidden=!job.accepted;
  if(job.state==='success'){notice(liveTranslation().complete);}
  else{notice((job.state==='warning'?liveTranslation().incomplete:liveTranslation().failed)+': '+job.message,true);}
 }catch(e){$('#installResult').hidden=false;$('#installResult').className='install-result error';$('#installResult').textContent=errorMessage(e);notice(errorMessage(e),true)}
 finally{setBusy(false);}
}
async function check(){setBusy(true,$('#checkBtn'));try{let res=await request('/api/check',{host:$('#zimaHost').value.trim(),internal_host:$('#internalZimaHost').value.trim(),username:$('#zimaUser').value.trim(),password:$('#zimaPassword').value,name:appName});$('#installResult').hidden=false;$('#installResult').className='install-result';$('#installResult').textContent=res.verified?JSON.stringify(res.containers,null,2):`${res.message} (HTTP ${res.code})`;$('#installResult').style.whiteSpace='pre-wrap';}catch(e){notice(errorMessage(e),true)}finally{setBusy(false);}}
// Starting a new installation must never retain the previous project's source,
// generated Compose, credentials, catalog filters, or partially finished review.
// Installed NAS apps and global settings (language, GitHub token, session) stay put.
function resetNewInstallation(){
 if(busy&&step===4)return; // Never abandon an installation already running on the NAS.
 ++wizardGeneration;
 ++settingsGeneration;
 clearTimeout(settingsTimer);settingsTimer=null;
 if(selfhstAppsSearchTimer)clearTimeout(selfhstAppsSearchTimer);
 selfhstAppsSearchTimer=null;++selfhstAppsSearchSeq;
 selfhstAppsRemoteQuery='';selfhstAppsRemoteRows=[];selfhstAppsRemotePage=0;
 selfhstAppsRemoteTotal=0;selfhstAppsRemoteMore=false;
 selfhstAppsRemoteBusy=false;selfhstAppsRemoteError='';
 lsioSelected='';
 imStoreProvider='mine';
 $$('.im-store-provider').forEach(b=>{const active=b.dataset.storeProvider==='mine';b.classList.toggle('is-active',active);b.setAttribute('aria-pressed',String(active));});
 kind='image';source='';appName='';planReady=false;installed=false;
 // Switch back to the first source tab; setSourceType may recreate #sourceInput.
 setSourceType('image');
 for(const id of [
  'sourceInput','containerPort','hostPort','configPath',
  'lsioSearch','selfhstAppsSearch','imStoresMySearch',
  'appName','appTitle','dataDir','iconUrl','sourceYaml',
  'iconSearchInput','generatedCompose',
  'tailscaleAuthKey','cloudflareTunnelToken',
  'internalZimaHost','zimaUser','zimaPassword','installTotpCode'
 ]){const element=$('#'+id);if(element)element.value='';}
 $('#lsioCategory').value='';$('#lsioSelection').hidden=true;$('#lsioSelection').textContent='';
 $('#selfhstAppsTag').value='';selfhstAppsSortMode='new';
 $('#imTargetSystem').value='zimaos';
 $('#category').value='Others';
 if(lsioImages)renderLsio();
 selfhstAppsUpdateSortTabs();
 $('#selfhstAppsGitHubStatus').textContent=sl('idle');
 $('#selfhstAppsGitHubMore').hidden=true;
 // Keep the catalog cache, but remove every search and selection.
 if(selfhstApps)renderSelfhstApps();
 showSourceDiagnosis(null);
 for(const id of ['resolvedSource','projectSource']){
  const el=$('#'+id);el.hidden=true;
  if(id==='resolvedSource')el.textContent='';
 }
 $('#projectLink').textContent='';$('#projectLink').removeAttribute('href');
 showPublisherSuggestions([]);resetProjectIcons();
 drawProfiles([]);setupLaterProfiles.clear();
 $('#buildDeferred').hidden=true;
 $('#requiredComposeFields').replaceChildren();$('#requiredComposeFields').hidden=true;
 for(const id of ['composeSettingsPanel','accessPanel']){
  const el=$('#'+id);el.replaceChildren();el.hidden=true;
 }
 $('#portList').replaceChildren();
 hostHardware=null;$('#resourceServiceList').replaceChildren();
 $('#hardwareSummary').textContent='';
 timezoneInfo=null;timezoneTouched=false;
 $('#timezoneName').dataset.loaded='';$('#timezoneName').value='Europe/Berlin';
 $('#timezoneAddMissing').checked=false;setTimezoneMode('original');
 $('#previewInfo').textContent='';
 $('#readinessHeading').textContent='';$('#readinessPanel').classList.remove('blocked');
 $('#setupIssues').replaceChildren();
 $('#setupLaterReview').replaceChildren();$('#setupLaterReview').hidden=true;
 $('#fixSetupBtn').hidden=true;
 $('#technicalDetails').hidden=true;$('#technicalDetails').open=false;
 $('#technicalSummary').textContent='';$('#warnings').replaceChildren();
 $('#proceedBtn').disabled=true;
 $('#confirmInstall').checked=false;$('#confirmBuild').checked=false;
 $('#buildConsent').hidden=true;
 $('#installResult').hidden=true;$('#installResult').textContent='';
 $('#installResult').className='install-result';
 $('#installLive').hidden=true;
 for(const id of ['installTimeline','installContainers','installEvents'])$('#'+id).replaceChildren();
 $('#installLiveTitle').textContent='';$('#installElapsed').textContent='00:00';
 $('#checkBtn').hidden=true;liveStarted=0;
 $('#proxyTotpBox').hidden=true;
 updateDeferredHint();
 selectStep(1);
 setBusy(false);
 updateInstallAction();
}

function closeInstallSettings(){
 const panel=$('#settingsDialog');
 if(panel.open)panel.close();
 $('#settingsButton').setAttribute('aria-expanded','false');
 const menu=$('#imLanguageMenu');if(menu)menu.hidden=true;
 panel.classList.remove('im-language-open');
 const toggle=$('#imLanguageToggle');if(toggle)toggle.setAttribute('aria-expanded','false');
}
function syncInstallHeaderHeight(){
 const header=document.querySelector('#app > .main-header');
 if(!header)return;
 document.documentElement.style.setProperty('--im-header-height',Math.ceil(header.getBoundingClientRect().height)+'px');
}
function syncInstallSettingsTop(){
 const header=document.querySelector('.main-header');
 if(!header)return;
 const bottom=Math.max(0,Math.round(header.getBoundingClientRect().bottom));
 document.documentElement.style.setProperty('--im-settings-top',bottom+'px');
}
function openInstallSettings(){
 const panel=$('#settingsDialog');
 syncInstallSettingsTop();
 if(!panel.open)panel.show();
 $('#settingsButton').setAttribute('aria-expanded','true');
 setupAuthenticatorStatus();proxyHostsRefresh();imGhRefresh();
}
function bind(){translate();syncInstallHeaderHeight();window.addEventListener('resize',syncInstallHeaderHeight);if(window.ResizeObserver){new ResizeObserver(syncInstallHeaderHeight).observe(document.querySelector('#app > .main-header'));}updateBuildConsentText();$('#imLanguageToggle').addEventListener('click',()=>{const menu=$('#imLanguageMenu');menu.hidden=!menu.hidden;$('#settingsDialog').classList.toggle('im-language-open',!menu.hidden);$('#imLanguageToggle').setAttribute('aria-expanded',String(!menu.hidden))});$$('#imLanguageMenu [data-lang]').forEach(b=>b.addEventListener('click',()=>{$('#language').value=b.dataset.lang;$('#language').dispatchEvent(new Event('change',{bubbles:true}));$('#imLanguageMenu').hidden=true;$('#settingsDialog').classList.remove('im-language-open');$('#imLanguageToggle').setAttribute('aria-expanded','false')}));document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('#imLanguageMenu').hidden=true;$('#settingsDialog').classList.remove('im-language-open');$('#imLanguageToggle').setAttribute('aria-expanded','false')}});document.addEventListener('click',e=>{if(!e.target.closest('#imLanguagePicker')){$('#imLanguageMenu').hidden=true;$('#settingsDialog').classList.remove('im-language-open');$('#imLanguageToggle').setAttribute('aria-expanded','false')}});$('#language').addEventListener('change',e=>{lang=e.target.value;localStorage.setItem('installMonitorLanguage',lang);translate();if(currentSourceDiagnosis)showSourceDiagnosis(currentSourceDiagnosis);if(selfhstApps)renderSelfhstApps();updateBuildConsentText();showRequiredComposeFields();refreshSettings();renderIconPicker();renderResources(true);renderTimezone();translateAdditionalUI();setupAuthenticatorStatus();proxyHostsRefresh();imAboutRefresh()});$('#loginForm').addEventListener('submit',async e=>{e.preventDefault();const pass=$('#loginPassword').value;$('#loginError').textContent='';try{const res=await request('/api/login',{username:$('#loginUsername').value.trim(),password:pass},false);csrf=res.csrf;$('#loginPassword').value='';showApp()}catch(e){$('#loginError').textContent=errorMessage(e)}});$('#settingsButton').onclick=(event)=>{event.stopPropagation();if($('#settingsDialog').open){closeInstallSettings();return;}openInstallSettings()};document.addEventListener('pointerdown',event=>{const panel=$('#settingsDialog');if(panel.open&&!panel.contains(event.target)&&!$('#settingsButton').contains(event.target))closeInstallSettings()});document.addEventListener('keydown',event=>{if(event.key==='Escape'&&$('#settingsDialog').open){event.preventDefault();closeInstallSettings()}});$('#settingsDialog').addEventListener('close',()=>$('#settingsButton').setAttribute('aria-expanded','false'));window.addEventListener('resize',()=>{if($('#settingsDialog').open)syncInstallSettingsTop()});$('#proxyHostAdd').onclick=()=>proxyHostChange($('#proxyHostName').value.trim().toLowerCase(),false);$('#authenticatorBegin').onclick=beginAuthenticator;$('#authenticatorConfirm').onclick=confirmAuthenticator;$('#zimaHost').addEventListener('input',updateProxyTotp);$('#zimaHost').addEventListener('change',()=>{void saveZimaOsTarget().catch(e=>notice(errorMessage(e),true));});$('#logoutBtn').onclick=async()=>{await request('/api/logout',{});$('#settingsDialog').close();$('#settingsButton').setAttribute('aria-expanded','false');showLogin()};$$('.source-tab').forEach(b=>b.onclick=()=>{setSourceType(b.dataset.kind);if(kind!=='lsio')$('#sourceInput').value='';showSourceDiagnosis(null);});$$('.im-store-provider').forEach(b=>b.addEventListener('click',()=>imChangeStoreProvider(b.dataset.storeProvider)));$('#imStoresMySearch').addEventListener('input',imRenderMyStore);$('#imStoresRefresh').addEventListener('click',()=>void imLoadMyStore(true));$('#imStoresLsioAnalyze').addEventListener('click',()=>{if(!lsioSelected||busy)return;setSourceType('lsio');$('#sourceInput').value=lsioSelected;void analyze()});$('#lsioSearch').addEventListener('input',renderLsio);$('#lsioCategory').addEventListener('change',renderLsio);$('#selfhstAppsSearch').addEventListener('input',selfhstAppsQueueGitHub);$('#selfhstAppsTag').addEventListener('change',renderSelfhstApps);$$('.im-selfhst-sort-tab').forEach(btn=>btn.addEventListener('click',()=>{selfhstAppsSortMode=btn.dataset.catalogSort;renderSelfhstApps()}));$('#selfhstAppsGitHubMore').onclick=selfhstAppsMoreGitHub;$('#analyzeBtn').onclick=analyze;$('#iconRescan').onclick=()=>searchProjectIcons(iconProjectUrl,true,$('#iconSearchInput').value.trim());$('#iconSearchSubmit').onclick=()=>searchProjectIcons(iconProjectUrl,false,$('#iconSearchInput').value.trim());$('#iconSourceFilter').addEventListener('change',()=>searchProjectIcons(iconProjectUrl,false,$('#iconSearchInput').value.trim()));$('#iconSearchInput').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();searchProjectIcons(iconProjectUrl,false,$('#iconSearchInput').value.trim())}});$('#iconUrl').addEventListener('input',renderIconPicker);let resourceChangeTimer=0;$('#sourceYaml').addEventListener('input',()=>{showRequiredComposeFields();scheduleSettings();clearTimeout(resourceChangeTimer);resourceChangeTimer=setTimeout(()=>renderResources(true),350)});$('#sourceYaml').addEventListener('change',()=>{renderResources(true);loadTimezone(false)});$('#imTargetSystem').addEventListener('change',()=>{planReady=false;$('#proceedBtn').disabled=true;});$('#hardwareRefresh').onclick=()=>loadHostResources(true);$('#timezoneRefresh').onclick=()=>loadTimezone(false);document.querySelectorAll('input[name="timezoneMode"]').forEach(node=>node.addEventListener('change',()=>{timezoneTouched=true;renderTimezone()}));$('#timezoneName').addEventListener('change',()=>{timezoneTouched=true});$('#timezoneAddMissing').addEventListener('change',()=>{timezoneTouched=true});$('#browseDataDir').onclick=()=>openFolderPicker(path=>{$('#dataDir').value=path},$('#dataDir').value);$('#folderDialogClose').onclick=()=>$('#folderDialog').close();$('#folderBrowseBack').onclick=()=>{const at=folderCurrent.lastIndexOf('/');loadFolder(at<=0?'':folderCurrent.slice(0,at))};$('#folderBrowseSelect').onclick=()=>{if(folderSelection&&folderCurrent){folderSelection(folderCurrent);$('#folderDialog').close()}};$('#previewBtn').onclick=preview;$('#checkPortsBtn').onclick=refreshPortScan;$('#tailscaleAuthKey').addEventListener('input',()=>{updateDeferredHint();});$('#tailscaleAuthKey').addEventListener('change',refreshPortScan);$('#cloudflareTunnelToken').addEventListener('input',updateDeferredHint);$('#backSource').onclick=()=>selectStep(1);$('#backConfig').onclick=()=>selectStep(2);$('#fixSetupBtn').onclick=()=>selectStep(2);$('#backPreview').onclick=()=>selectStep(3);$('#downloadBtn').onclick=downloadCompose;$('#proceedBtn').onclick=()=>{selectStep(4);void loadZimaOsTarget();void setupAuthenticatorStatus();updateProxyTotp()};$('#installBtn').onclick=install;$('#checkBtn').onclick=check;$('#newInstall').onclick=resetNewInstallation}
/* v0.1.69 — Update-Monitor-like logo information panel. */
let imAboutTimer=null;
function imAboutClose(){
 const panel=document.getElementById('imAboutPanel');if(panel)panel.hidden=true;
 const button=document.getElementById('imAboutButton');if(button)button.setAttribute('aria-expanded','false');
 if(imAboutTimer){clearInterval(imAboutTimer);imAboutTimer=null;}
}
async function imAboutRefresh(){
 const panel=document.getElementById('imAboutPanel');if(!panel||panel.hidden)return;
 try{const r=await request('/api/about');
  const set=(id,value)=>{const e=document.getElementById(id);if(e)e.textContent=value};
  const fmt=new Intl.DateTimeFormat(lang==='de'?'de-DE':lang==='pt'?'pt-PT':lang==='fr'?'fr-FR':lang==='es'?'es-ES':'en-GB',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
  set('imAboutCpu',typeof r.cpu_percent==='number'?r.cpu_percent.toFixed(1)+' %':ux('aboutUnavailable'));
  set('imAboutMemory',typeof r.memory_mb==='number'?Math.round(r.memory_mb)+' MB':ux('aboutUnavailable'));
  set('imAboutSince',r.started_at?fmt.format(new Date(r.started_at*1000)):ux('aboutUnavailable'));
  set('imAboutVersion','v'+(r.version||'0.2.54'));
  set('imAboutManagement',r.zimaos_app_management===true?ux('aboutDetected'):r.zimaos_app_management===false?ux('aboutNotDetected'):ux('aboutNotChecked'));
 }catch(e){for(const id of ['imAboutCpu','imAboutMemory','imAboutSince']){const el=document.getElementById(id);if(el)el.textContent=ux('aboutUnavailable')}}
}

/* v0.2.7: GitHub PAT settings, without exposing the stored credential. */
const imGhText={
 de:{hint:'Persönlichen GitHub-Token für höhere API-Limits speichern. Der Schlüssel bleibt auf dem NAS.',label:'GitHub Personal Access Token',save:'Speichern',test:'Verbindung testen',remove:'Entfernen',empty:'Kein GitHub-Token eingerichtet.',configured:'Token gespeichert.',env:'Token über Docker-Umgebungsvariable konfiguriert.',saved:'GitHub-Token gespeichert.',deleted:'Gespeicherten GitHub-Token entfernt.',wait:'GitHub wird geprüft …',failed:'Verbindung fehlgeschlagen: ',account:'Konto',quota:'API-Restkontingent',reset:'Zurücksetzung',bad:'Bitte gültigen GitHub-Token eingeben.',confirm:'Gespeicherten GitHub-Token entfernen?'},
 en:{hint:'Save a personal GitHub token for higher API limits. The token stays on your NAS.',label:'GitHub personal access token',save:'Save',test:'Test connection',remove:'Remove',empty:'No GitHub token configured.',configured:'Token saved.',env:'Token configured in Docker environment.',saved:'GitHub token saved.',deleted:'Saved GitHub token removed.',wait:'Checking GitHub …',failed:'Connection failed: ',account:'Account',quota:'API requests remaining',reset:'Resets',bad:'Enter a valid GitHub token.',confirm:'Remove saved GitHub token?'},
 fr:{hint:'Enregistrer un jeton GitHub pour augmenter les limites API. Il reste sur le NAS.',label:'Jeton d’accès personnel GitHub',save:'Enregistrer',test:'Tester la connexion',remove:'Supprimer',empty:'Aucun jeton GitHub configuré.',configured:'Jeton enregistré.',env:'Jeton défini dans Docker.',saved:'Jeton enregistré.',deleted:'Jeton supprimé.',wait:'Vérification GitHub …',failed:'Échec de connexion : ',account:'Compte',quota:'Requêtes restantes',reset:'Réinitialisation',bad:'Saisissez un jeton GitHub valide.',confirm:'Supprimer le jeton GitHub ?'},
 pt:{hint:'Guardar um token GitHub para aumentar os limites da API. Fica no NAS.',label:'Token de acesso pessoal GitHub',save:'Guardar',test:'Testar ligação',remove:'Remover',empty:'Nenhum token GitHub configurado.',configured:'Token guardado.',env:'Token configurado no Docker.',saved:'Token guardado.',deleted:'Token removido.',wait:'A verificar GitHub …',failed:'Falha na ligação: ',account:'Conta',quota:'Pedidos restantes',reset:'Reinicia',bad:'Introduza um token GitHub válido.',confirm:'Remover o token GitHub?'},
 es:{hint:'Guardar un token GitHub para aumentar los límites de la API. Se queda en el NAS.',label:'Token de acceso personal GitHub',save:'Guardar',test:'Probar conexión',remove:'Eliminar',empty:'Ningún token GitHub configurado.',configured:'Token guardado.',env:'Token configurado en Docker.',saved:'Token guardado.',deleted:'Token eliminado.',wait:'Comprobando GitHub …',failed:'Error de conexión: ',account:'Cuenta',quota:'Solicitudes restantes',reset:'Se reinicia',bad:'Introduce un token GitHub válido.',confirm:'¿Eliminar el token GitHub guardado?'}
};
function imGhLang(){return imGhText[lang]||imGhText.de}
function imGhTranslate(){
 const t=imGhLang();
 const heading=$('#ghHeading');if(!heading)return;
 $('#ghHint').textContent=t.hint;$('#ghTokenLabel').textContent=t.label;
 $('#ghTokenSave').textContent=t.save;$('#ghTokenTest').textContent=t.test;$('#ghTokenRemove').textContent=t.remove;
}
function imGhStatus(status){
 const t=imGhLang(),statusLine=$('#ghTokenStatus');if(!statusLine)return;
 let label=!status.configured?t.empty:status.source==='umgebung'?t.env:t.configured;
 if(status.login)label+=' · '+t.account+': '+status.login;
 if(typeof status.remaining==='number'&&typeof status.limit==='number')label+=' · '+t.quota+': '+status.remaining+'/'+status.limit;
 if(status.reset){const d=new Date(status.reset*1000);if(!isNaN(d))label+=' · '+t.reset+': '+d.toLocaleString(lang==='de'?'de-DE':lang==='pt'?'pt-PT':lang==='fr'?'fr-FR':lang==='es'?'es-ES':'en-GB');}
 statusLine.textContent=label;
 $('#ghTokenTest').disabled=!status.configured;
 $('#ghTokenRemove').disabled=status.source!=='gespeichert';
}
async function imGhRefresh(){
 try{imGhStatus(await request('/api/github/settings'))}
 catch(e){$('#ghTokenStatus').textContent=errorMessage(e)}
}
async function imGhSave(){
 const t=imGhLang(),value=$('#ghTokenInput').value.trim();
 if(!/^[A-Za-z0-9_-]{20,300}$/.test(value)){$('#ghTokenStatus').textContent=t.bad;return;}
 $('#ghTokenSave').disabled=true;
 try{imGhStatus(await request('/api/github/settings',{token:value}));$('#ghTokenInput').value='';notice(t.saved)}
 catch(e){$('#ghTokenStatus').textContent=errorMessage(e)}
 finally{$('#ghTokenSave').disabled=false}
}
async function imGhTest(){
 const t=imGhLang();$('#ghTokenTest').disabled=true;$('#ghTokenStatus').textContent=t.wait;
 try{imGhStatus(await request('/api/github/test',{}))}
 catch(e){$('#ghTokenStatus').textContent=t.failed+errorMessage(e)}
 finally{$('#ghTokenTest').disabled=false}
}
async function imGhRemove(){
 const t=imGhLang();if(!window.confirm(t.confirm))return;
 try{imGhStatus(await request('/api/github/remove',{}));$('#ghTokenInput').value='';notice(t.deleted)}
 catch(e){$('#ghTokenStatus').textContent=errorMessage(e)}
}
function imGhBind(){
 imGhTranslate();
 $('#ghTokenSave').onclick=imGhSave;$('#ghTokenTest').onclick=imGhTest;$('#ghTokenRemove').onclick=imGhRemove;
 $('#language').addEventListener('change',()=>{imGhTranslate();imGhRefresh()});
}

function imAboutBind(){
 const btn=document.getElementById('imAboutButton'),panel=document.getElementById('imAboutPanel');if(!btn||!panel)return;
 btn.addEventListener('click',e=>{e.stopPropagation();const wasOpen=!panel.hidden;imAboutClose();if(wasOpen)return;
   if(document.getElementById('settingsDialog')?.open)closeInstallSettings();
   panel.hidden=false;btn.setAttribute('aria-expanded','true');imAboutRefresh();imAboutTimer=setInterval(imAboutRefresh,5000);
 });
 document.addEventListener('pointerdown',e=>{if(!panel.hidden&&!panel.contains(e.target)&&!btn.contains(e.target))imAboutClose()});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden){e.preventDefault();imAboutClose()}});
 document.getElementById('settingsButton')?.addEventListener('click',()=>imAboutClose());
}


async function start(){installBrowserBackGuard();bind();imAboutBind();imGhBind();try{let s=await request('/api/session');if(s.authenticated){csrf=s.csrf;showApp()}else showLogin()}catch(e){showLogin();$('#loginError').textContent=errorMessage(e)}}
start();
})();


/* v0.2.41 – language-style dropdowns outside Settings only. The original select stays the
   source of truth; native value, options and change handlers are preserved. */
(()=>{'use strict';
 const entries=new WeakMap();
 let nextId=0,active=null,frame=0;
 const all=()=>[...document.querySelectorAll('select:not(.im-language-native)')].filter(node=>!node.closest('#settingsDialog'));
 const menu=document.createElement('div');
 menu.className='im-modern-menu';menu.hidden=true;menu.setAttribute('role','listbox');
 const outline=document.createElement('div');outline.className='im-modern-open-outline';outline.hidden=true;outline.setAttribute('aria-hidden','true');
 menu.id='imModernSelectMenu';
 const labelFor=select=>select.id?Array.from(document.querySelectorAll('label[for]')).find(l=>l.htmlFor===select.id):null;
 function sync(select){
  const entry=entries.get(select);if(!entry)return;
  if(!select.isConnected){if(active===entry)close();return;}
  const option=select.selectedOptions[0]||null;
  const label=option?.textContent?.trim()||select.getAttribute('placeholder')||'—';
  if(entry.label.textContent!==label)entry.label.textContent=label;
  const disabled=select.disabled||select.options.length===0;
  if(entry.button.disabled!==disabled)entry.button.disabled=disabled;
  if(entry.wrapper.hidden!==select.hidden)entry.wrapper.hidden=select.hidden;
  const accessible=select.getAttribute('aria-label')||labelFor(select)?.textContent?.trim()||select.closest('div')?.querySelector('label')?.textContent?.trim()||select.title||'Select';
  if(entry.button.getAttribute('aria-label')!==accessible)entry.button.setAttribute('aria-label',accessible);
  if(active===entry&&(!select.isConnected||disabled||entry.wrapper.closest('[hidden]')))close();
 }
 function enhance(select){
  if(entries.has(select)||!select.isConnected)return;
  const wrapper=document.createElement('span');wrapper.className='im-modern-select';
  const trigger=document.createElement('button');trigger.type='button';trigger.className='im-modern-trigger';
  const text=document.createElement('span');text.className='im-modern-label';
  const arrow=document.createElement('span');arrow.className='im-modern-arrow';arrow.setAttribute('aria-hidden','true');
  trigger.append(text,arrow);trigger.setAttribute('aria-haspopup','listbox');
  trigger.setAttribute('aria-expanded','false');trigger.setAttribute('aria-controls',menu.id);
  wrapper.hidden=select.hidden;
  select.replaceWith(wrapper);wrapper.append(select,trigger);
  select.classList.add('im-modern-native');select.tabIndex=-1;select.setAttribute('aria-hidden','true');
  const entry={select,wrapper,button:trigger,label:text};entries.set(select,entry);
  trigger.addEventListener('click',()=>active===entry?close():open(entry));
  trigger.addEventListener('keydown',e=>{
   if(['ArrowDown','ArrowUp','Enter',' '].includes(e.key)){
    e.preventDefault();if(active!==entry)open(entry);
    const buttons=[...menu.querySelectorAll('.im-modern-option:not(:disabled)')];
    if(buttons.length){(e.key==='ArrowUp'?buttons[buttons.length-1]:buttons[0]).focus();}
   }
  });
  select.addEventListener('change',()=>sync(select));
  select.addEventListener('input',()=>sync(select));
  sync(select);
 }
 function place(){
  if(!active||menu.hidden)return;
  const r=active.button.getBoundingClientRect();
  if(!r.width||!r.height){close();return;}
  const margin=8,availableBelow=innerHeight-r.bottom-margin,availableAbove=r.top-margin;
  const want=Math.min(340,Math.max(90,menu.scrollHeight));
  const above=availableBelow<Math.min(170,want)&&availableAbove>availableBelow;
  const space=Math.max(65,above?availableAbove:availableBelow);
  const h=Math.min(want,space);
  const width=Math.max(0,Math.min(r.width,innerWidth-margin*2));
  const left=Math.max(margin,Math.min(r.left,innerWidth-width-margin));
  const side=above?'above':'below';
  menu.dataset.side=side;active.button.dataset.side=side;
  menu.style.width=width+'px';
  menu.style.maxHeight=h+'px';
  menu.style.left=left+'px';
  menu.style.top=(above?Math.max(margin,r.top-h+1):r.bottom-1)+'px';
  menu.style.borderRadius=above?'7px 7px 0 0':'0 0 7px 7px';
  // Never use the desired max-height for the frame: short lists may render
  // smaller than that limit (two 41px options versus the 90px minimum).
  // Using max-height drew a second blue bottom line below the real menu.
  if(above){
   const naturalHeight=menu.getBoundingClientRect().height;
   menu.style.top=Math.max(margin,r.top-naturalHeight+1)+'px';
  }
  const actual=menu.getBoundingClientRect();
  // Trigger/menu borders stay geometrically present, but transparent.
  // Only this one outer overlay renders the visible blue perimeter.
  const outerLeft=Math.min(r.left,actual.left);
  const outerRight=Math.max(r.right,actual.right);
  const outerTop=Math.min(r.top,actual.top);
  const outerBottom=Math.max(r.bottom,actual.bottom);
  outline.style.left=outerLeft+'px';outline.style.top=outerTop+'px';
  outline.style.width=(outerRight-outerLeft)+'px';
  outline.style.height=(outerBottom-outerTop)+'px';
  outline.hidden=false;
 }
 function open(entry){
  if(entry.button.disabled)return;
  close();sync(entry.select);
  active=entry;
  menu.replaceChildren();
  const fragment=document.createDocumentFragment();
  // Read current options on each opening: catalogs, translations and dynamic
  // configuration can replace the list at runtime.
  for(const option of entry.select.options){
   const item=document.createElement('button');item.type='button';item.className='im-modern-option';
   item.setAttribute('role','option');item.setAttribute('aria-selected',String(option.selected));
   item.dataset.value=option.value;item.textContent=option.textContent||'—';
   item.disabled=option.disabled||(option.parentElement instanceof HTMLOptGroupElement&&option.parentElement.disabled);
   item.addEventListener('click',()=>{
    if(item.disabled)return;
    const changed=entry.select.value!==option.value;
    entry.select.value=option.value;
    close();sync(entry.select);
    if(changed){entry.select.dispatchEvent(new Event('input',{bubbles:true}));entry.select.dispatchEvent(new Event('change',{bubbles:true}));}
    entry.button.focus({preventScroll:true});
   });
   fragment.appendChild(item);
  }
  menu.appendChild(fragment);
  entry.button.setAttribute('aria-expanded','true');
  menu.hidden=false;place();
  const chosen=menu.querySelector('.im-modern-option[aria-selected="true"]');
  if(chosen)chosen.scrollIntoView({block:'nearest'});
 }
 function close(){
  if(!active)return;
  active.button.setAttribute('aria-expanded','false');delete active.button.dataset.side;active=null;
  menu.hidden=true;menu.replaceChildren();outline.hidden=true;
 }
 function repaint(){
  frame=0;
  for(const select of all()){if(!entries.has(select))enhance(select);else sync(select);}
  if(active)place();
 }
 function schedule(){if(!frame)frame=requestAnimationFrame(repaint);}
 menu.addEventListener('keydown',e=>{
  if(!active)return;
  const items=[...menu.querySelectorAll('.im-modern-option:not(:disabled)')];
  if(e.key==='Escape'){e.preventDefault();const b=active.button;close();b.focus({preventScroll:true});return;}
  if(e.key==='Tab'){close();return;}
  if(!['ArrowDown','ArrowUp','Home','End','Enter',' '].includes(e.key))return;
  e.preventDefault();
  const index=items.indexOf(document.activeElement);
  if(e.key==='Enter'||e.key===' '){if(index>=0)items[index].click();return;}
  let next=e.key==='Home'?0:e.key==='End'?items.length-1:e.key==='ArrowDown'?Math.min(index+1,items.length-1):Math.max(index-1,0);
  if(next<0)next=0;if(items[next])items[next].focus();
 });
 document.addEventListener('pointerdown',e=>{
  if(active&&!active.wrapper.contains(e.target)&&!menu.contains(e.target))close();
 },true);
 document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&active){const button=active.button;close();button.focus({preventScroll:true});}
 },true);
 document.addEventListener('click',e=>{
  const label=e.target.closest('label[for]');if(!label)return;
  const select=document.getElementById(label.htmlFor);const entry=entries.get(select);
  if(entry){e.preventDefault();entry.button.focus();}
 });
 document.addEventListener('scroll',e=>{if(active&&e.target!==menu)place();},true);
 window.addEventListener('resize',()=>{if(active)place();});
 const observer=new MutationObserver(records=>{
  // Rebuild only if a select's option subtree changes; ordinary app rendering
  // cannot recursively rebuild the currently open list.
  if(active&&records.some(r=>r.target===active.select||active.select.contains(r.target))){
   const old=active;close();schedule();old.button.focus({preventScroll:true});
  }else schedule();
 });
 document.body.append(menu,outline);
 repaint();
 observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['disabled','selected','value','label','hidden']});
})();
