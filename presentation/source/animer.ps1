# Montage : transitions et animations, posées par PowerPoint lui-même.
# Usage : powershell -File animer.ps1 <source.pptx> <sortie.pptx>
#
# Règles (cohérentes avec ce que chaque élément représente) :
#  - ordre de lecture : les éléments sont créés dans l'ordre de lecture (gauche à droite, haut en bas) ;
#    chaque étape démarre après la précédente ;
#  - une carte (fond + titre + texte + formule qu'elle contient) apparaît d'un bloc ;
#  - barre verticale : pousse depuis l'axe (du bas vers le haut) ; barre horizontale : pousse depuis l'axe
#    (de gauche à droite) ; étiquette avec la barre, valeur ensuite, puis barre suivante ;
#  - anneau : se remplit en tournant ; courbe : se trace de gauche à droite ; flèche : se trace dans le sens du flux ;
#  - barre de section, titre, pied de page et cadres de la page de garde : fixes (le Morph les garde en place).
param([string]$Source, [string]$Sortie)

$app = New-Object -ComObject PowerPoint.Application
$p = $app.Presentations.Open($Source, $false, $false, $false)

$Fade = 10; $Wipe = 22; $Zoom = 23; $Wheel = 21
$AfterPrevious = 3; $WithPrevious = 2
$PousseHaut = 1; $PousseDroite = 2; $DepuisHaut = 3   # codes vérifiés : 1 = wipe(up), 2 = wipe(right), 3 = wipe(down)
$Morph = 3953; $FadeSmoothly = 3849
$PT = 72.0

function Dans($c, $sh) {
    $m = 0.06 * $PT
    return ($sh.Left -ge $c.Left - $m) -and ($sh.Top -ge $c.Top - $m) -and
           ($sh.Left + $sh.Width -le $c.Left + $c.Width + $m) -and ($sh.Top + $sh.Height -le $c.Top + $c.Height + $m)
}

$numero = 0
foreach ($s in $p.Slides) {
    $numero++
    $s.SlideShowTransition.EntryEffect = $Morph
    if ($s.SlideShowTransition.EntryEffect -ne $Morph) { $s.SlideShowTransition.EntryEffect = $FadeSmoothly }
    $s.SlideShowTransition.Duration = 0.8

    $seq = $s.TimeLine.MainSequence
    while ($seq.Count -gt 0) { $seq.Item(1).Delete() }

    # 1. Formes à animer, dans l'ordre de création (ordre de lecture)
    $formes = @()
    $i = 0
    foreach ($sh in $s.Shapes) {
        $i++
        $txt = ""
        if ($sh.HasTextFrame) { $txt = $sh.TextFrame.TextRange.Text }
        if ($txt -match "^\d+ / \d+$" -or ($sh.Top -gt 6.9 * $PT -and $sh.Height -lt 0.4 * $PT)) { continue }   # pied de page (repéré par sa position)
        if ($numero -gt 1 -and $i -le 3) { continue }                     # barre de section, son texte, titre
        if ($sh.Width -gt 12 * $PT) { continue }                          # cadres et bandeaux pleine largeur
        $formes += $sh
    }

    # 2. Étapes : une carte et ce qu'elle contient ; une barre avec son étiquette et sa valeur ; sinon un élément seul
    $etapes = New-Object System.Collections.ArrayList
    $prises = @{}
    foreach ($sh in $formes) {
        if ($prises.ContainsKey($sh.Name)) { continue }
        $etape = New-Object System.Collections.ArrayList
        if ($sh.Name -match "^(lab|barreV|barreH|val)(\d+)$") {
            $n = $Matches[2]
            foreach ($nom in @("lab$n", "barreV$n", "barreH$n", "val$n")) {
                foreach ($o in $formes) { if ($o.Name -eq $nom -and -not $prises.ContainsKey($o.Name)) { [void]$etape.Add($o); $prises[$o.Name] = 1 } }
            }
        }
        elseif ($sh.HasChart -or ($sh.Type -eq 1 -and ($sh.AutoShapeType -in 1, 5, 9) -and (-not $sh.HasTextFrame -or $sh.TextFrame.TextRange.Text -eq ""))) {
            [void]$etape.Add($sh); $prises[$sh.Name] = 1
            foreach ($o in $formes) { if (-not $prises.ContainsKey($o.Name) -and $o.Name -notmatch "^(lab|barre|val)" -and (Dans $sh $o)) { [void]$etape.Add($o); $prises[$o.Name] = 1 } }
        }
        else { [void]$etape.Add($sh); $prises[$sh.Name] = 1 }
        [void]$etapes.Add($etape)
    }

    # 2 bis. Fusion des étapes liées : un texte seul rejoint l'étape précédente s'il en est le titre ou la légende
    #        (même colonne, juste en dessous) ou s'il est sur la même ligne qu'un bloc (description d'un niveau d'entonnoir)
    $fusion = New-Object System.Collections.ArrayList
    foreach ($etape in $etapes) {
        $b = $etape[0]
        $seul = ($etape.Count -eq 1) -and $b.HasTextFrame -and $b.Type -ne 1 -and -not $b.HasChart
        if ($fusion.Count -gt 0 -and $seul) {
            $prec = $fusion[$fusion.Count - 1]
            $a = $prec[$prec.Count - 1]
            $tete = $prec[0]
            $memeColonne = [Math]::Abs($b.Left - $a.Left) -le 0.35 * $PT
            $juste = ($b.Top - ($a.Top + $a.Height)) -le 0.3 * $PT -and $b.Top -ge $a.Top
            $memeLigne = ($tete.Type -eq 1) -and ([Math]::Abs($b.Top - $tete.Top) -le 0.15 * $PT) -and ($b.Left -gt $tete.Left)
            if (($memeColonne -and $juste -and $a.Name -notmatch "^(lab|barre|val)") -or $memeLigne) { [void]$prec.Add($b); continue }
        }
        [void]$fusion.Add($etape)
    }
    $etapes = $fusion

    # 3. Effets
    $premiere = $true
    foreach ($etape in $etapes) {
        $j = 0
        foreach ($sh in $etape) {
            $declencheur = $(if ($j -eq 0) { $AfterPrevious } else { $WithPrevious })
            if ($sh.Type -eq 16) {   # vidéo : lecture automatique, sans effet d'entrée
                try { $sh.AnimationSettings.PlaySettings.PlayOnEntry = -1; $sh.AnimationSettings.PlaySettings.HideWhileNotPlaying = 0 } catch {}
                $j++; continue
            }
            if ($sh.Name -like "barreV*") {
                $e = $seq.AddEffect($sh, $Wipe, 0, $declencheur); $e.EffectParameters.Direction = $PousseHaut; $e.Timing.Duration = 0.5
            }
            elseif ($sh.Name -like "barreH*") {
                $e = $seq.AddEffect($sh, $Wipe, 0, $declencheur); $e.EffectParameters.Direction = $PousseDroite; $e.Timing.Duration = 0.5
            }
            elseif ($sh.Name -like "val*") {
                $e = $seq.AddEffect($sh, $Fade, 0, $WithPrevious); $e.Timing.Duration = 0.25; $e.Timing.TriggerDelayTime = 0.4
            }
            elseif ($sh.HasChart -and ($sh.Chart.ChartType -eq -4120 -or $sh.Chart.ChartType -eq 5)) {
                $e = $seq.AddEffect($sh, $Wheel, 0, $declencheur); $e.Timing.Duration = 1.0
            }
            elseif ($sh.HasChart) {   # courbe
                $e = $seq.AddEffect($sh, $Wipe, 0, $declencheur); $e.EffectParameters.Direction = $PousseDroite; $e.Timing.Duration = 1.2
            }
            elseif ($sh.Type -eq 9) {   # flèche : tracée dans le sens du flux
                $e = $seq.AddEffect($sh, $Wipe, 0, $declencheur); $e.EffectParameters.Direction = $PousseDroite; $e.Timing.Duration = 0.4
            }
            elseif ($sh.HasTable) {
                $e = $seq.AddEffect($sh, $Wipe, 0, $declencheur); $e.EffectParameters.Direction = $DepuisHaut; $e.Timing.Duration = 0.6
            }
            elseif ($sh.Type -eq 13) {   # image ou formule
                $e = $seq.AddEffect($sh, $Fade, 0, $declencheur); $e.Timing.Duration = 0.5
            }
            else {
                $e = $seq.AddEffect($sh, $Fade, 0, $declencheur); $e.Timing.Duration = 0.4
            }
            if ($j -eq 0 -and -not $premiere) { $e.Timing.TriggerDelayTime = 0.05 }
            if ($j -eq 0 -and $premiere) { $e.Timing.TriggerDelayTime = 0.2 }
            $j++
        }
        $premiere = $false
    }
    "diapositive {0} : {1} étapes, {2} effets" -f $numero, $etapes.Count, $seq.Count
}

$p.SaveAs($Sortie)
$p.Close()
$app.Quit()
"montage écrit : $Sortie"
