"""Resolution-independent DirectGUI screens and persistent native sliders.

Controls rebuild on navigation/layout changes, never during a drag gesture.
"""
from math import degrees
from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectOptionMenu, DirectEntry, DirectSlider
from panda3d.core import TextNode, LineSegs
from domain import Scene
from fortress import SPECS
from lessons import LESSONS
from profile_store import FPS_OPTIONS
from theme import INK, PANEL, RAISED, PURPLE, GOLD, AQUA, GREEN, RED, WHITE, MUTED, TERM_COLOURS


class Interface:
    WIDTH,HEIGHT = 1440,900

    def __init__(self,app):
        self.app = app
        self.root = app.pixel2d.attachNewNode('interface')
        self.widgets=[]; self.labels={}; self.sliders={}; self.buttons=[]
        self.rects=[]; self.focus=-1; self.signature=None
        self.generation=0; self.large=False
        self.resize()

    def resize(self):
        w,h=self.app.win.getXSize(),self.app.win.getYSize()
        self.scale=min(w/self.WIDTH,h/self.HEIGHT)
        self.offset=((w-self.WIDTH*self.scale)/2,(h-self.HEIGHT*self.scale)/2)
        self.root.setScale(self.scale); self.root.setPos(self.offset[0],0,-self.offset[1])
        self.signature=None

    def text(self,value,x,y,size=18,colour=WHITE,width=0,key=None,align=TextNode.ALeft):
        text=TextNode('label'); text.setText(str(value)); text.setTextColor(*colour); text.setAlign(align)
        font=self.app.font_bold if size>=24 else self.app.font
        if font:text.setFont(font)
        effective=size*(1.10 if self.large and size<=20 else 1)
        if width:text.setWordwrap(width/effective)
        n=self.root.attachNewNode(text);n.setScale(effective);n.setPos(x,0,-y-effective)
        if key:self.labels[key]=text
        return text

    def panel(self,x,y,w,h,colour=PANEL):
        if self.app.prefs['high_contrast'] and colour==PANEL:colour=(.055,.045,.12,1)
        shadow=DirectFrame(parent=self.root,pos=(x+5,0,-y-6),frameSize=(0,w,-h,0),frameColor=(0,0,0,.35),relief=None)
        f=DirectFrame(parent=self.root,pos=(x,0,-y),frameSize=(0,w,-h,0),frameColor=colour,relief=DGG.RIDGE,borderWidth=(2,2))
        self.widgets.extend((shadow,f));self.rects.append((x,y,w,h));return f

    def button(self,title,x,y,w,callback,colour=PURPLE,h=42,enabled=True,key=None):
        generation=self.generation
        def guarded():
            if generation!=self.generation or not enabled:return
            self.app.audio.play('click',self.app.prefs);callback()
        fg=INK if colour in (GOLD,AQUA,GREEN,RED) else WHITE
        if not enabled:colour,fg=RAISED,MUTED
        b=DirectButton(parent=self.root,pos=(x+w/2,0,-y-h/2),frameSize=(-w/2,w/2,-h/2,h/2),
            text=title,text_scale=19 if len(title)<28 else 17,text_fg=fg,text_pos=(0,-6),text_font=self.app.font_bold,
            frameColor=(colour,colour,tuple(min(1,c*1.16) for c in colour[:3])+(1,),RAISED),
            relief=DGG.RAISED,borderWidth=(2,2),pressEffect=True,command=guarded,state=DGG.NORMAL if enabled else DGG.DISABLED)
        self.widgets.append(b);self.rects.append((x,y,w,h))
        if enabled:self.buttons.append((b,guarded,title))
        if key:self.labels[key]=b
        return b

    def menu(self,items,current,x,y,w,callback):
        m=DirectOptionMenu(parent=self.root,pos=(x,0,-y),items=list(items),initialitem=current,
            scale=17,text_scale=1,text_fg=WHITE,text_font=self.app.font,frameColor=RAISED,highlightColor=PURPLE,relief=DGG.RAISED,
            command=callback,popupMarker_pos=(w/17-1,0,0),frameSize=(0,w/17,-1.65,.4),item_frameColor=PANEL,item_text_fg=WHITE)
        self.widgets.append(m);self.rects.append((x,y-10,w,40));return m

    def numeric(self,key,value,x,y,w,low,high,callback):
        entry=DirectEntry(parent=self.root,pos=(x,0,-y),scale=17,width=w/17,initialText=f'{value:.2f}',numLines=1,text_font=self.app.font,
            focus=0,frameColor=INK,text_fg=WHITE,relief=DGG.SUNKEN,borderWidth=(.1,.1))
        def apply(text=None):
            try:
                number=float(entry.get())
                if not low<=number<=high:raise ValueError()
            except ValueError:
                self.app.notice=f'Enter a number from {low} to {high}.'
                entry.enterText(f'{self.sliders[key]["value"] if key in self.sliders else value:.2f}');return
            callback(number);entry['focus']=0
        entry['command']=apply
        self.widgets.append(entry);self.rects.append((x,y-18,w,30));return entry

    def slider(self,key,value,x,y,w,high,callback,step=.05):
        entry=self.numeric(key,value,x+w-71,y+4,64,0,high,lambda v:self.set_slider(key,v))
        slider=DirectSlider(parent=self.root,pos=(x+(w-90)/2,0,-y),range=(0,high),value=value,pageSize=step,
            frameSize=(-(w-90)/2,(w-90)/2,-6,6),frameColor=INK,relief=DGG.SUNKEN,
            thumb_frameSize=(-9,9,-13,13),thumb_frameColor=AQUA,thumb_relief=DGG.RAISED)
        def changed():
            v=round(slider['value'],3);callback(v)
            if not entry['focus']:entry.enterText(f'{v:.2f}')
        slider['command']=changed;self.sliders[key]=slider;self.widgets.append(slider)
        self.rects.append((x,y-16,w,32));return slider

    def set_slider(self,key,value):
        if key in self.sliders:
            slider=self.sliders[key];slider['value']=value;slider.commandFunc()

    def rebuild(self):
        for w in self.widgets:w.destroy()
        self.root.getChildren().detach()
        self.widgets=[];self.labels={};self.sliders={};self.buttons=[];self.rects=[];self.focus=-1;self.generation+=1
        a=self.app;self.large=a.prefs['large_text'];self.toolbar()
        if a.screen=='title':self.title()
        elif a.screen=='options':self.options()
        elif a.screen=='map':self.map()
        elif a.screen=='academy_hub':self.academy_hub()
        elif a.screen=='records':self.records()
        elif a.screen=='contract':self.contract()
        elif a.screen in ('campaign','academy'):
            self.battle_controls()
            if a.screen=='campaign' and a.campaign.finished:self.campaign_result()
            if a.screen=='academy':self.academy_overlay()
        if a.display.pending is not None:self.display_confirmation()

    def toolbar(self):
        a=self.app;self.panel(16,12,1408,76,INK)
        self.text('LEAD THE TARGET',36,25,27,GOLD);self.text('FORTRESS / CONTROL QUEST',37,58,11,MUTED)
        self.button('Campaign',355,28,125,lambda:a.navigate('map'),AQUA)
        self.button('Academy',490,28,125,lambda:a.navigate('academy_hub'))
        self.button('Records',625,28,110,lambda:a.navigate('records'))
        self.button('Options',745,28,110,a.open_options)
        self.text('',875,30,16,GREEN,key='wallet');self.button('Home',1267,28,130,lambda:a.navigate('title'))
        self.button('Expand controls' if a.prefs['compact'] else 'Compact mode',1194,846,220,a.toggle_compact,AQUA,h=38)
        self.text('',28,852,15,GOLD,width=1140,key='notice')

    def title(self):
        a=self.app;self.panel(55,160,660,620)
        self.text('BUILD A FORTRESS.',88,190,39,WHITE);self.text('AIM INTO THE FUTURE.',88,239,39,GOLD)
        self.text('A tank keeps moving while your shell flies.\nPredict its next move. Make every shot count.',90,315,23,WHITE,570)
        self.button('CONTINUE CAMPAIGN',90,420,510,a.enter_campaign,GOLD,h=60)
        self.button('Visit the academy',90,495,246,lambda:a.navigate('academy_hub'),AQUA,h=52)
        self.button('Choose a level',351,495,249,lambda:a.navigate('map'),h=52)
        self.text('100 encounters / 12 build pads / 4 tower types',90,580,20,GREEN,550)
        self.text('Rushes, armour and flanking convoys. Build, upgrade and rebuild after defeat. Learn interception and PIDF through measured experiments.',90,625,18,MUTED,535)
        self.text('Mouse: select pads   |   Space: pause   |   C: compact\nTab + Enter: navigate buttons   |   Esc: back',90,717,15,MUTED,550)

    def map(self):
        a=self.app;c=a.campaign;self.panel(45,110,1350,710)
        self.text('CAMPAIGN / 100 ENCOUNTERS',78,132,30,GOLD)
        self.text('Earn credits, expand your fortress, adapt to the next attack. Completed levels can be replayed.',78,178,18,MUTED,1200)
        chapter=a.map_page
        from waves import REGIONS,LEVELS
        self.text(f'{chapter+1:02} / {REGIONS[chapter]}',78,239,27,WHITE)
        max_level=min(100,max([int(k)+1 for k in c.completed]+[c.level]))
        for i in range(10):
            number=chapter*10+i+1;done=str(number) in c.completed;x=83+(i%5)*253;y=315+(i//5)*155
            self.button(f'{number:02}   '+('CLEARED' if done else 'DEFEND' if number<=max_level else 'LOCKED'),x,y,225,
                lambda n=number:a.enter_campaign(n),GREEN if done else GOLD,h=70,enabled=number<=max_level)
            self.text(LEVELS[number-1].title,x,y+82,17,MUTED,230)
        self.button('< Previous region',80,708,240,lambda:a.change_map(-1),enabled=chapter>0)
        self.button('Next region >',1050,708,240,lambda:a.change_map(1),enabled=chapter<9)
        self.text(f'Current: level {c.level}   |   Site {c.site+1}   |   {len(c.towers)} towers',360,719,20,AQUA)

    def academy_hub(self):
        a=self.app;self.panel(45,110,1350,710);self.text('THE ACADEMY',78,132,32,GOLD)
        self.text('Try a prediction. Observe the result. Prove it in a changed scenario. Mastery rewards fund your fortress.',78,183,19,MUTED,1220)
        from curriculum import STEPS
        for i,lesson in enumerate(LESSONS):
            x=80+(i%2)*650;y=265+(i//2)*120;count=sum(k.startswith(f'{i}:') for k in a.academy.learning)
            self.button(lesson.title,x,y,600,lambda s=i:a.enter_academy(s),GREEN if count==len(STEPS[i]) else PURPLE,h=49)
            self.text(f'{count}/{len(STEPS[i])} tasks demonstrated  /  {lesson.subtitle}',x+4,y+58,16,MUTED,595)

    def battle_controls(self):
        a=self.app;compact=a.prefs['compact']
        if compact:
            self.panel(16,594,1408,240);self.tuning_controls(40,608,420,True)
            self.coach(490,612,475,True);self.instruments(995,610,395,True)
        else:
            self.panel(1010,108,414,725);self.tuning_controls(1032,123,368,False)
            self.coach(1032,555,368,False);self.instruments(34,674,500,False)
        if a.screen=='campaign':
            c=a.campaign;self.panel(28,108,680,78);self.text(f'LEVEL {c.level:02} / {c.spec.region.upper()}',46,120,22,GOLD)
            self.text('',46,152,17,WHITE,key='battle_status')
            self.button('Pause / resume' if c.running else 'LAUNCH ATTACK',738,114,245,a.launch_or_pause,GOLD,h=52)
            self.text('',40,206,17,WHITE,760,key='incoming')
            y=537 if compact else 600
            self.button('Build towers',30,y,175,a.toggle_build,AQUA);self.button('Recovery task',218,y,175,a.recovery)
            self.button('Relocate troops',406,y,185,a.relocate,RED,enabled=not c.running)
            if a.building:
                self.panel(35,265,520,260);self.text('BUILD / SELECT A PAD ON THE ISLAND',55,281,20,GOLD)
                for i,(kind,spec) in enumerate(SPECS.items()):
                    self.button(f'{spec.title}  /  {spec.cost}c',55+(i%2)*244,330+(i//2)*65,230,
                        lambda k=kind:a.choose_build(k),AQUA if a.build_kind==kind else PURPLE,enabled=c.level>=spec.unlock)
                self.text(f'Choose a tower, then click an empty numbered pad.\nSelected pad: {a.build_pad+1 if a.build_pad is not None else "none"}',55,467,16,MUTED,470)
        else:
            g=a.academy;self.panel(28,108,900,66);self.text(g.lesson.title,46,122,27,GOLD)
            if g.mode==Scene.EXPERIMENT:self.text('EXPERIMENT RUNNING / watch the shell and cyan prediction',47,179,19,AQUA)

    def tuning_controls(self,x,y,w,compact):
        a=self.app
        if a.screen=='campaign':
            t=a.campaign.selected
            if not t:return
            name=f'{t.spec.title} #{t.id} / pad {t.pad+1} / upgrade {t.level}'
            algorithm,lead,gains=t.algorithm,t.lead,t.gains;unlocked=a.campaign.unlock
        else:
            g=a.academy;name='EXPERIMENT EQUIPMENT' if g.mode==Scene.EXPERIMENT else 'TARGETING / CONTROL'
            algorithm,lead,gains=g.algorithm,g.lead,g.gains();unlocked=g.unlock
        self.text(name,x,y,18,GOLD,w);names=['Direct','Fixed lead','Intercept','Adaptive','Colour aware'][:unlocked+1]
        self.menu(names,algorithm,x,y+45,w,lambda choice:a.set_algorithm(names.index(choice)))
        self.text('Lead time / seconds',x,y+78,15,AQUA)
        self.slider('lead',lead,x+30,y+114,w-62,2,a.set_lead)
        self.button('-',x,y+100,26,lambda:a.adjust_lead(-.05),AQUA,h=30)
        self.button('+',x+w-28,y+100,28,lambda:a.adjust_lead(.05),AQUA,h=30)
        if compact:
            self.button('Full tuning + upgrades',x,y+155,w,a.toggle_compact,h=36);return
        for i,label in enumerate(('P / correct','I / remember','D / damp','F / anticipate')):
            yy=y+151+i*49;self.text(label,x,yy,14,TERM_COLOURS[i])
            self.slider('pidf'[i],gains[i],x+106,yy+16,w-106,(16,5,2,3)[i],lambda v,n=i:a.set_gain(n,v),.1)
        if a.screen=='campaign':
            t=a.campaign.selected;self.button(f'Upgrade / {t.upgrade_cost}c',x,y+361,175,a.upgrade,enabled=t.level<3)
            self.button(f'Sell / {t.refund}c',x+185,y+361,w-185,a.sell,RED)
        else:self.button('Colour input ON' if a.academy.colour_enabled else 'Colour input OFF',x,y+361,w,a.toggle_colour,AQUA)

    def coach(self,x,y,w,compact):
        a=self.app
        if a.screen=='campaign':
            c=a.campaign;t=c.selected;self.text('FORTRESS ORDERS',x,y,20,GOLD);self.text(c.spec.briefing,x,y+35,16,WHITE,w)
            if compact:self.text(c.message,x,y+115,15,AQUA,w);return
            self.text(t.spec.description if t else '',x,y+116,15,MUTED,w)
            self.menu(('First','Nearest','Strongest'),('First','Nearest','Strongest').index(t.priority),x,y+179,168,a.set_priority)
            self.button('Copy tuning',x+178,y+162,w-178,a.copy_tuning,h=36)
            self.button('Colour sensor / 80c' if not t.colour else 'Colour ON' if t.sensor_enabled else 'Colour OFF',x,y+214,w,a.toggle_colour,AQUA,h=37)
        else:
            g=a.academy;step=g.step;self.text('TRY / OBSERVE / EXPLAIN',x,y,20,GOLD)
            if step:
                self.text(step.title,x,y+35,19,WHITE,w);self.text(step.task,x,y+68,15,MUTED,w)
                if not compact:self.text('See the task panel for results and next steps.',x,y+213,14,AQUA,w)

    def instruments(self,x,y,w,compact):
        self.panel(x-8,y-8,w+16,207 if compact else 158,INK);self.text('LIVE TELEMETRY / SELECTED TOWER',x,y,16,AQUA)
        self.text('',x,y+29,15,WHITE,w,key='telemetry')
        for i,(term,col) in enumerate(zip('PIDF',TERM_COLOURS)):
            self.text('',x+(i%2)*(w/2),y+87+(i//2)*24,15,col,key=f'term_{term}')
        self.text('',x,y+139,14,MUTED,w,key='actual_gains');self.graph_root=self.root.attachNewNode('live-graph')
        self.graph_rect=(x,y+171,w,27) if compact else (x+w+26,y+8,410,115)

    def academy_overlay(self):
        a=self.app;g=a.academy
        if g.mode==Scene.CONGRATS:
            self.panel(210,190,790,460);self.text('*  *  *',605,213,48,GOLD,align=TextNode.ACenter)
            record=g.learning.get(g.runner.pending,{});self.text('WELL DONE, COMMANDER!',250,289,30,GOLD)
            self.text(record.get('title','Lesson complete'),250,340,24,WHITE,695)
            self.text(record.get('why',g.lesson.subtitle),250,390,18,MUTED,695)
            evidence=record.get('evidence',{});desc=[]
            for key in ('miss_distance','rms_error','steady_error','overshoot'):
                if key in evidence:desc.append(f'{key.replace("_"," ")}: {evidence[key]:.2f}')
            self.text(' / '.join(desc) or 'Reasoning verified and saved.',250,487,17,AQUA,690)
            self.text('Mastery reward: 10 campaign credits (once per task)',250,539,17,GREEN)
            self.button('Continue',685,574,265,a.continue_academy,GOLD,h=50)
        elif g.mode in (Scene.COACH,Scene.READY):
            step=g.step
            if not step:return
            self.panel(30,205,900,385);self.text(step.title,53,220,27,GOLD);self.text(step.task,53,263,19,WHITE,845)
            self.text(g.runner.feedback or 'Make a prediction, then test it. Settings alone do not complete a task.',53,354,17,RED if g.runner.feedback else MUTED,845,key='academy_feedback')
            if step.kind=='choice':
                for i,option in enumerate(step.options):self.button(option,54,424+i*47,845,lambda v=option:a.answer(v),h=39)
            elif step.kind=='trial':
                self.button('RUN EXPERIMENT',53,441,350,a.run_experiment,GOLD,h=52);self.button('Show a hint',423,441,210,a.show_hint)
                self.button('Explain physics',648,441,250,a.show_explanation,AQUA)
            elif step.kind=='purchase':self.button('Install + verify colour sensor',53,441,520,a.verify_sensor,GOLD,h=52)
            else:self.button('LAUNCH FIELD CHALLENGE',53,441,500,a.launch_academy_wave,GOLD,h=52)
        elif g.mode==Scene.RESULT:
            self.panel(145,230,790,400);self.text('FIELD SECURED' if g.success else 'TRY A DIFFERENT MODEL',185,257,32,GOLD)
            self.text(f'{g.hits} hits / {g.shots} shots / {g.health} fortress health',185,320,24,WHITE)
            self.text(g.result_hint,185,366,18,MUTED,700);self.button('Review task',185,504,330,a.academy_retry,GOLD)
            self.button('Academy map',535,504,330,lambda:a.navigate('academy_hub'))
        elif g.mode==Scene.VICTORY:
            self.panel(150,220,800,390);self.text('ACADEMY MASTERED',190,257,36,GOLD)
            self.text('Your evidence is saved. Take your models and tuning into the 100-level campaign.',190,330,24,WHITE,700)
            self.button('Defend the fortress',190,485,680,a.enter_campaign,GOLD,h=60)

    def campaign_result(self):
        a=self.app;c=a.campaign;self.panel(170,240,795,390)
        self.text('*  *  *' if c.success else 'FORTRESS OVERRUN',210,265,36,GOLD if c.success else RED)
        self.text(f'LEVEL {c.level} '+('SECURED' if c.success else '/ RELOCATE TROOPS'),210,330,28,WHITE)
        self.text(f'{c.kills} tanks stopped / {c.hits} hits / {c.shots} shells / {max(0,c.health)} health',210,381,20,AQUA)
        self.text(c.message,210,424,18,MUTED,710)
        self.button('Next encounter' if c.success and c.level<100 else 'Return to fortress',210,527,345,a.next_encounter,GOLD,h=53)
        self.button('Replay level' if c.success else 'Relocate troops',575,527,345,a.replay_encounter if c.success else a.relocate,AQUA,h=53)

    def options(self):
        a=self.app;d=a.display;self.panel(130,120,1180,690);self.text('DISPLAY & ACCESSIBILITY',168,147,32,GOLD)
        w,h=a.win.getXSize(),a.win.getYSize();self.text(f'Detected screen: {d.desktop[0]} x {d.desktop[1]} / Current game: {w} x {h}',168,198,20,AQUA)
        chosen=dict(a.prefs);self.text('Resolution',170,259,20,WHITE)
        resolutions=[f'{x} x {y}' for x,y in d.resolutions];current=f'{a.prefs["resolution"][0]} x {a.prefs["resolution"][1]}'
        self.menu(resolutions,resolutions.index(current),170,310,380,lambda s:chosen.update(resolution=[int(v) for v in s.split(' x ')]))
        self.text('Display mode',610,259,20,WHITE);modes=('Windowed','Borderless','Fullscreen')
        self.menu(modes,modes.index(a.prefs['display_mode']),610,310,490,lambda s:chosen.update(display_mode=s))
        fps=[str(v) if v else 'Uncapped' for v in FPS_OPTIONS];self.text('Frame rate limit',170,365,20,WHITE)
        self.menu(fps,FPS_OPTIONS.index(a.prefs['fps']),170,415,380,lambda s:chosen.update(fps=0 if s=='Uncapped' else int(s)))
        self.text('VSync may cap FPS at your monitor refresh rate.',610,373,18,MUTED,490)
        self.button('VSync: ON' if chosen['vsync'] else 'VSync: OFF',610,413,490,lambda:a.toggle_pref('vsync'),AQUA)
        for i,(key,title) in enumerate((('compact','Bottom compact controls'),('large_text','Larger text'),('reduced_motion','Reduced motion'),('high_contrast','High contrast'),('muted','Mute sound'))):
            self.button(f'{title}: '+('ON' if a.prefs[key] else 'OFF'),170+(i%2)*480,488+(i//2)*57,450,lambda k=key:a.toggle_pref(k))
        self.text('Physics stays at 120 Hz at every FPS setting. Borderless uses the desktop resolution.',170,686,17,MUTED,1050)
        self.button('APPLY DISPLAY',170,738,450,lambda:a.apply_display(chosen),GOLD,h=48);self.button('Back',650,738,450,a.close_options,AQUA,h=48)

    def display_confirmation(self):
        a=self.app;self.panel(365,280,710,280,INK);self.text('KEEP THESE DISPLAY SETTINGS?',397,310,27,GOLD)
        self.text('',397,365,20,WHITE,630,key='countdown');self.button('Keep settings',398,458,299,a.confirm_display,GREEN,h=55)
        self.button('Revert',717,458,299,a.revert_display,RED,h=55)

    def records(self):
        a=self.app;c=a.campaign;self.panel(110,130,1220,665);self.text('COMMANDER RECORD',150,161,32,GOLD)
        self.text(f'{len(c.completed)} / 100 sectors defended',150,236,30,WHITE)
        self.text(f'{len(a.academy.learning)} academy tasks proved / {len(c.towers)} deployed towers',150,290,25,AQUA)
        self.text('LOCAL RECORDS',150,370,23,GOLD)
        for i,(level,record) in enumerate(sorted(a.records.items(),key=lambda kv:int(kv[0]))[-7:]):
            self.text(f'Level {int(level):02}: {record["health"]} health / {record["shots"]} shots / {record["seconds"]:.1f}s',150,414+i*34,19,WHITE)
        self.text('Online leaderboards are planned. This build records your results locally.',150,724,18,MUTED,1050)

    def contract(self):
        a=self.app;t=a.contract
        self.panel(180,180,1080,560)
        self.text('CONTRACT COMPLETE!' if t['done'] else 'RECOVERY / QUARTERMASTER CONTRACT',220,215,30,GOLD)
        self.text(t['question'],220,285,24,WHITE,990)
        self.text(t['feedback'] or 'Calculate flight time first. Then find how far the tank moves.',220,390,20,GREEN if t['done'] else AQUA,990)
        if t['done']:self.button('Return to fortress',220,580,990,a.enter_campaign,GOLD,h=60)
        else:
            for i,option in enumerate(t['options']):self.button(option,220,480+i*62,990,lambda v=option:a.answer_contract(v),h=50)

    def refresh(self):
        a=self.app;g=a.academy;c=a.campaign
        signature=(a.screen,g.mode if a.screen=='academy' else '',g.runner.pending,g.step.id if a.screen=='academy' and g.step else '',
            c.finished,c.selected_id,a.prefs['compact'],a.prefs['large_text'],a.prefs['high_contrast'],a.prefs['muted'],a.prefs['vsync'],
            a.building,a.build_kind,a.build_pad,a.map_page,a.display.pending is not None,c.selected.level if c.selected else 0,
            c.selected.colour if c.selected else False,c.selected.sensor_enabled if c.selected else False)
        if signature!=self.signature:self.signature=signature;self.rebuild()
        self.set_text('wallet',f'{c.credits} CREDITS / SITE {c.site+1}')
        self.set_text('notice',a.notice or (c.message if a.screen=='campaign' else a.save_note))
        if a.display.pending is not None:self.set_text('countdown',f'Automatically reverts in {a.display.remaining} seconds. Esc also reverts.')
        self.set_text('battle_status',f'HEALTH {max(0,c.health)}/16   /   {c.kills} STOPPED   /   {c.shots} SHELLS   /   {c.time:05.1f}s')
        next_spawns=c.spec.spawns[c.spawned:c.spawned+3]
        self.set_text('incoming','INCOMING  /  '+'  |  '.join(f'{s.time-c.time:.1f}s: {s.colour.upper()} at gate {s.entrance+1}' for s in next_spawns) if next_spawns else 'All attacks deployed / clear the remaining tanks')
        if a.screen not in ('campaign','academy'):return
        if a.screen=='academy':
            trial=g.trial if g.mode==Scene.EXPERIMENT else None;motor=trial.tower if trial else g.tower
            gains=trial.gains if trial else g.gains();sol=trial.solution if trial else g.solution
            wait='Calibration: fixed equipment' if trial else g.wait_reason;history=trial.samples if trial and trial.tracking else ();sample=motor.controller.sample
        else:
            t=c.selected
            if not t:return
            motor=t.motor;gains=t.gains;sol=t.solution;wait=t.wait;sample=motor.controller.sample;history=c.history
        self.set_text('telemetry',f'{wait}\nError {degrees(sample.error):+.2f} deg / output {degrees(sample.output):+.1f} deg/s\n'+(f'Flight {sol.flight_time:.2f}s / {sol.branch}' if sol else 'No current intercept'))
        for term in 'PIDF':self.set_text('term_'+term,f'{term}: {degrees(getattr(sample,term.lower())):+.1f} deg/s')
        self.set_text('actual_gains','ACTIVE gains: '+' / '.join(f'{t} {v:.2f}' for t,v in zip('PIDF',gains)))
        if hasattr(self,'graph_root') and not self.graph_root.isEmpty():self.graph(history)

    def graph(self,history):
        self.graph_root.getChildren().detach();x,y,w,h=self.graph_rect;samples=list(history)[-150:]
        if len(samples)<2:return
        for attr,colour in (('error',WHITE),('p',AQUA),('i',GOLD),('d',RED),('f',GREEN)):
            ls=LineSegs();ls.setThickness(1.6);ls.setColor(*colour)
            for i,row in enumerate(samples):
                v=max(-90,min(90,degrees(getattr(row[1],attr))));p=(x+i*w/(len(samples)-1),0,-y-h/2+v*h/180)
                if i==0:ls.moveTo(*p)
                else:ls.drawTo(*p)
            self.graph_root.attachNewNode(ls.create())

    def set_text(self,key,value):
        target=self.labels.get(key)
        if target:
            if isinstance(target,TextNode):target.setText(value)
            else:target['text']=value

    def pointer_on_ui(self):
        if not self.app.mouseWatcherNode.hasMouse():return True
        m=self.app.mouseWatcherNode.getMouse();w,h=self.app.win.getXSize(),self.app.win.getYSize()
        x=((m.x+1)*w/2-self.offset[0])/self.scale;y=((1-m.y)*h/2-self.offset[1])/self.scale
        return any(rx<=x<=rx+rw and ry<=y<=ry+rh for rx,ry,rw,rh in self.rects)

    def focus_next(self):
        if not self.buttons:return
        if self.focus>=0:self.buttons[self.focus][0]['relief']=DGG.RAISED
        self.focus=(self.focus+1)%len(self.buttons);self.buttons[self.focus][0]['relief']=DGG.RIDGE

    def activate_focus(self):
        if 0<=self.focus<len(self.buttons):self.buttons[self.focus][1]()

    def editing(self):return any(isinstance(w,DirectEntry) and w['focus'] for w in self.widgets)
