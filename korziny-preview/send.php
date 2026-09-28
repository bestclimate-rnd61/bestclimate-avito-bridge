<?php
// Smart lead handler v2 for korziny.bestclimate-rnd.ru
// Place in public_html as send.php. Settings stay outside public_html in ../lead-config.php.
// PHP 7.4+ with cURL. Bot token is never exposed to browser code.
ini_set('display_errors', '0');
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function reply($status, $ok, $message, $extra = []) {
    http_response_code($status);
    echo json_encode(array_merge(['ok'=>$ok,'message'=>$message], $extra), JSON_UNESCAPED_UNICODE);
    exit;
}
set_exception_handler(function () { reply(500, false, 'Не удалось отправить заявку. Свяжитесь с нами напрямую.'); });

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST'); reply(405, false, 'Используйте форму на сайте.');
}
if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 32 * 1024 * 1024) {
    reply(413, false, 'Фотографии слишком большие. Загрузите до 5 фото меньшего размера.');
}
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$requestHost = strtolower(trim((string)($_SERVER['HTTP_X_FORWARDED_HOST'] ?? $_SERVER['HTTP_HOST'] ?? '')));
$requestHost = preg_replace('/:\d+$/', '', $requestHost);
$originHost = $origin !== '' ? strtolower((string)parse_url($origin, PHP_URL_HOST)) : '';
$allowedOrigins = ['https://korziny.bestclimate-rnd.ru','http://korziny.bestclimate-rnd.ru'];
$sameOriginHost = ($originHost !== '' && $requestHost !== '' && hash_equals($requestHost, $originHost));
if ($origin !== '' && !$sameOriginHost && !in_array($origin, $allowedOrigins, true)) {
    reply(403, false, 'Отправьте заявку с нашего сайта.');
}

function field($name, $limit) {
    $value = $_POST[$name] ?? '';
    if (!is_string($value) || !preg_match('//u', $value)) reply(422, false, 'Некорректное поле формы.');
    $value = trim($value);
    if (preg_match_all('/./us', $value) > $limit || preg_match('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/', $value)) {
        reply(422, false, 'Сократите текст в полях формы.');
    }
    return $value;
}
if (field('website',300) !== '') reply(422,false,'Не удалось отправить форму.');
if (field('consent',10) !== '1') reply(422,false,'Подтвердите согласие на обработку данных.');

$limits = [
  'product'=>100,'qty'=>7,'size_mode'=>30,'size'=>200,'model'=>200,'ral'=>80,'city'=>200,
  'install'=>100,'contact'=>200,'comment'=>1200,'source_url'=>500,'utm_source'=>100,'utm_campaign'=>150
];
$data=[];
foreach($limits as $key=>$limit) $data[$key]=field($key,$limit);

if ($data['contact']==='') reply(422,false,'Укажите телефон, Telegram или e-mail.');
if ($data['qty']!=='' && !preg_match('/^[1-9][0-9]{0,5}$/D',$data['qty'])) reply(422,false,'Укажите количество от 1 до 999999.');

$referencePrices = [
  'Корзина для кондиционера'=>7500,
  'Кронштейны'=>690,
  'Подставка одноуровневая'=>2470,
  'Подставка двухуровневая'=>5850,
];
$qty = $data['qty'] !== '' ? (int)$data['qty'] : 1;
$unit = $referencePrices[$data['product']] ?? 0;
$total = $unit ? $unit * max(1,$qty) : 0;

// Basic anti-spam rate limit.
$rateDir = dirname(__DIR__) . '/lead-rate';
if (!is_dir($rateDir) && !@mkdir($rateDir,0700,true) && !is_dir($rateDir)) reply(503,false,'Сервис временно недоступен.');
$bucket = substr(hash('sha256', $_SERVER['REMOTE_ADDR'] ?? 'unknown'),0,3);
$lock = @fopen($rateDir.'/'.$bucket.'.json','c+');
if (!$lock || !flock($lock,LOCK_EX)) reply(503,false,'Сервис временно недоступен.');
$state=json_decode(stream_get_contents($lock),true); $now=time();
if (!is_array($state) || $now-($state['start']??0)>=600) $state=['start'=>$now,'count'=>0];
if ($state['count']>=5){flock($lock,LOCK_UN);fclose($lock);reply(429,false,'Слишком много попыток. Попробуйте через 10 минут.');}
$state['count']++; rewind($lock); ftruncate($lock,0); fwrite($lock,json_encode($state)); fflush($lock); flock($lock,LOCK_UN); fclose($lock);

// Secret configuration.
// Production host: ../lead-config.php. Railway preview: environment variables.
$config=[];
$configPath=dirname(__DIR__).'/lead-config.php';
if (is_file($configPath)) {
    ob_start();
    try { $loaded=require $configPath; if(is_array($loaded)) $config=$loaded; }
    catch(Throwable $e) { $config=[]; }
    ob_end_clean();
}
$token=$config['telegram_bot_token']??getenv('TELEGRAM_BOT_TOKEN')??'';
$chat=$config['telegram_chat_id']??getenv('TELEGRAM_CHAT_ID')??'';
if (!is_string($token) || !preg_match('/^[0-9]+:[A-Za-z0-9_-]+$/D',$token)
 || !is_scalar($chat) || !preg_match('/^-?[0-9]+$/D',(string)$chat) || !function_exists('curl_init')) {
    reply(503,false,'Отправка ещё не настроена.');
}

$id=bin2hex(random_bytes(6));
$fmtMoney=function($n){return number_format((float)$n,0,',',' ').' ₽';};
$text="🔥 НОВАЯ ЗАЯВКА — КОРЗИНЫ\n";
$text.="Номер: ".$id."\n";
$text.="Дата UTC: ".gmdate('Y-m-d H:i:s')."\n\n";
$labels=[
 'product'=>'Изделие','qty'=>'Количество','size_mode'=>'Размеры','size'=>'Размер корзины / ниши',
 'model'=>'Модель / размер наружного блока','ral'=>'Цвет','city'=>'Город / объект',
 'install'=>'Формат','contact'=>'Контакт','comment'=>'Комментарий'
];
foreach($labels as $key=>$label) $text.=$label.': '.($data[$key]!==''?$data[$key]:'не указано')."\n";
$text.="\nПредварительный ориентир: ".($unit ? $fmtMoney($unit).' / ед.' : 'по расчёту');
if($total) $text.="\nОриентир за партию: ".$fmtMoney($total);
$text.="\nИсточник: ".($data['source_url']!==''?$data['source_url']:'не определён');
if($data['utm_source']!=='') $text.="\nUTM source: ".$data['utm_source'];
if($data['utm_campaign']!=='') $text.="\nUTM campaign: ".$data['utm_campaign'];
$text.="\n\n⚠️ Ориентир не является утверждённым прайсом или публичной офертой.";
$text.="\nСогласие на обработку данных и загруженных изображений: подтверждено.";

// Send the text lead first so the lead is not lost if image upload fails.
$curl=curl_init('https://api.telegram.org/bot'.$token.'/sendMessage');
curl_setopt_array($curl,[
 CURLOPT_POST=>true,
 CURLOPT_POSTFIELDS=>http_build_query(['chat_id'=>(string)$chat,'text'=>$text]),
 CURLOPT_RETURNTRANSFER=>true,CURLOPT_CONNECTTIMEOUT=>5,CURLOPT_TIMEOUT=>20,
 CURLOPT_SSL_VERIFYPEER=>true,CURLOPT_SSL_VERIFYHOST=>2
]);
$raw=curl_exec($curl); $http=curl_getinfo($curl,CURLINFO_HTTP_CODE); curl_close($curl);
$result=is_string($raw)?json_decode($raw,true):null;
if($http!==200 || !is_array($result) || empty($result['ok'])) reply(502,false,'Не удалось подтвердить отправку. Свяжитесь с нами напрямую.');

$photosSent=false; $photoCount=0;
if (isset($_FILES['photos']) && is_array($_FILES['photos']['name'] ?? null)) {
    $names=$_FILES['photos']['name']; $tmps=$_FILES['photos']['tmp_name']; $sizes=$_FILES['photos']['size']; $errors=$_FILES['photos']['error'];
    $count=min(count($names),5); $valid=[];
    $finfo=function_exists('finfo_open') ? finfo_open(FILEINFO_MIME_TYPE) : null;
    $allowed=['image/jpeg'=>'jpg','image/png'=>'png','image/webp'=>'webp'];
    for($i=0;$i<$count;$i++){
        if(($errors[$i]??UPLOAD_ERR_NO_FILE)===UPLOAD_ERR_NO_FILE) continue;
        if(($errors[$i]??UPLOAD_ERR_OK)!==UPLOAD_ERR_OK) continue;
        $tmp=$tmps[$i]??''; $size=(int)($sizes[$i]??0);
        if(!is_uploaded_file($tmp) || $size<=0 || $size>6*1024*1024) continue;
        $mime=$finfo ? finfo_file($finfo,$tmp) : (function_exists('mime_content_type')?mime_content_type($tmp):'');
        if(!isset($allowed[$mime])) continue;
        if(function_exists('getimagesize') && @getimagesize($tmp)===false) continue;
        $valid[]=['tmp'=>$tmp,'mime'=>$mime,'name'=>'photo-'.($i+1).'.'.$allowed[$mime]];
    }
    if($finfo) finfo_close($finfo);

    if(count($valid)===1){
        $v=$valid[0];
        $c=curl_init('https://api.telegram.org/bot'.$token.'/sendPhoto');
        curl_setopt_array($c,[
          CURLOPT_POST=>true,
          CURLOPT_POSTFIELDS=>['chat_id'=>(string)$chat,'caption'=>'📷 Фото к заявке '.$id,'photo'=>new CURLFile($v['tmp'],$v['mime'],$v['name'])],
          CURLOPT_RETURNTRANSFER=>true,CURLOPT_CONNECTTIMEOUT=>5,CURLOPT_TIMEOUT=>30,
          CURLOPT_SSL_VERIFYPEER=>true,CURLOPT_SSL_VERIFYHOST=>2
        ]);
        $r=curl_exec($c); $h=curl_getinfo($c,CURLINFO_HTTP_CODE); curl_close($c);
        $jr=is_string($r)?json_decode($r,true):null;
        $photosSent=($h===200 && is_array($jr) && !empty($jr['ok'])); $photoCount=$photosSent?1:0;
    } elseif(count($valid)>1){
        $post=['chat_id'=>(string)$chat]; $media=[];
        foreach($valid as $i=>$v){
            $key='p'.$i;
            $post[$key]=new CURLFile($v['tmp'],$v['mime'],$v['name']);
            $item=['type'=>'photo','media'=>'attach://'.$key];
            if($i===0) $item['caption']='📷 Фото к заявке '.$id;
            $media[]=$item;
        }
        $post['media']=json_encode($media,JSON_UNESCAPED_UNICODE);
        $c=curl_init('https://api.telegram.org/bot'.$token.'/sendMediaGroup');
        curl_setopt_array($c,[
          CURLOPT_POST=>true,CURLOPT_POSTFIELDS=>$post,CURLOPT_RETURNTRANSFER=>true,
          CURLOPT_CONNECTTIMEOUT=>5,CURLOPT_TIMEOUT=>45,
          CURLOPT_SSL_VERIFYPEER=>true,CURLOPT_SSL_VERIFYHOST=>2
        ]);
        $r=curl_exec($c); $h=curl_getinfo($c,CURLINFO_HTTP_CODE); curl_close($c);
        $jr=is_string($r)?json_decode($r,true):null;
        $photosSent=($h===200 && is_array($jr) && !empty($jr['ok']));
        $photoCount=$photosSent?count($valid):0;
    }
}

// E-mail remains a secondary copy.
$mailAccepted=false;
$email=$config['email_to']??getenv('LEAD_EMAIL_TO')??'';
if(is_string($email)&&filter_var($email,FILTER_VALIDATE_EMAIL)&&!preg_match('/[\r\n]/',$email)&&function_exists('mail')){
    try{
        $subject='=?UTF-8?B?'.base64_encode('Заявка с сайта '.$id).'?=';
        $headers="MIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nFrom: leads@korziny.bestclimate-rnd.ru";
        $mailAccepted=@mail($email,$subject,$text,$headers);
    }catch(Throwable $e){$mailAccepted=false;}
}
reply(200,true,'Заявка отправлена.',[
 'request_id'=>$id,'telegram_sent'=>true,'photos_sent'=>$photosSent,'photo_count'=>$photoCount,
 'email_accepted'=>$mailAccepted,'estimate_unit'=>$unit,'estimate_total'=>$total
]);
