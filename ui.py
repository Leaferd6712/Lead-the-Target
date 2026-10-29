"""Responsive arcade presentation. Widgets emit actions; lessons own assessment."""
import math
from collections import OrderedDict
import pygame
import theme
from audio import Audio
from domain import Scene
from curriculum import STEPS
from experiments import Experiment, calibration_gains
from lessons import LESSONS, UPGRADES
from renderer3d import Renderer3D
from targeting import TargetObservation, Vec2
from theme import BG, PANEL, INK, EDGE, TEXT, MUTED, GOLD, TEAL, GREEN, RED, BLUE, TERMS, ButtonArt, panel, star


class Interface:
    def __init__(self, game, window):
        self.game, self.window = game, window
        self.surface = pygame.Surface(window.get_size())
        self.WIDTH, self.HEIGHT = window.get_size()
        self.fonts, self.text_cache = {}, OrderedDict()
        self.buttons, self.sliders = [], {}
        self.focus = -1
        self.dragging = None
        self.active_slider = None
        self.mouse = (-1,-1)
        self.art = ButtonArt()
        self.renderer = Renderer3D()
        self.audio = Audio()
        pygame.display.set_icon(theme.app_icon())
        self.event_cursor = None
        self.quit, self.fullscreen = False, False
        self.windowed = window.get_size()
        self.wall_time = 0
        self.coach_scroll = self.max_scroll = 0
        self.show_why = False
        self.advanced = False
        self.algorithm_popup = False
        self.editing = None
        self.confirm_action = None
        self.confirm_text = ""
        self.last_scene = None
        self.last_task = None
        self.preview_key = None
        self.preview = None
        self.scroll_positions={}
        self.profile = {"frame_ms":0.0,"samples":0}

    def font(self, size, bold=False, mono=False):
        scale = 1.15 if self.game.settings["large_text"] else 1
        key = round(size*scale),bold,mono
        if key not in self.fonts:
            self.fonts[key] = (pygame.font.SysFont("Consolas,DejaVu Sans Mono",key[0]) if mono else
                               pygame.font.Font(None,key[0]+2) if bold else pygame.font.SysFont("Arial,DejaVu Sans",key[0]))
        return self.fonts[key]

    def text(self, value, x, y, size=20, colour=TEXT, bold=False, mono=False, shadow=False):
        key = str(value),size,colour,bold,mono,self.game.settings["large_text"]
        if key not in self.text_cache:
            self.text_cache[key] = self.font(size,bold,mono).render(str(value),True,colour)
            if len(self.text_cache)>2048:self.text_cache.popitem(last=False)
        image = self.text_cache[key]
        if shadow:
            self.surface.blit(self.font(size,bold,mono).render(str(value),True,INK),(x+2,y+2))
        self.surface.blit(image,(round(x),round(y)))
        return image.get_width()

    def wrap(self, value, x, y, width, size=20, colour=MUTED, bold=False):
        font=self.font(size,bold)
        line_height=font.get_linesize()+5
        for paragraph in str(value).split("\n"):
            line=""
            for word in paragraph.split():
                candidate=(line+" "+word).strip()
                if font.size(candidate)[0]>width and line:
                    self.text(line,x,y,size,colour,bold)
                    y+=line_height
                    line=word
                else:line=candidate
            if line:self.text(line,x,y,size,colour,bold)
            y+=line_height
        return y

    def button(self, rect, label, action, style="stone", enabled=True, selected=False, tip=""):
        rect=pygame.Rect(rect)
        hover=rect.collidepoint(self.mouse)
        pressed=hover and pygame.mouse.get_pressed()[0]
        self.surface.blit(self.art.get(rect.size,"aqua" if selected else style,hover,pressed,not enabled),rect)
        font=self.font(19,True)
        symbol=("play" if label.startswith(("Run ","Launch ","Continue")) else "pause" if label.startswith("Pause ") else
                "lock" if label.startswith("Locked") else "shop" if label in ("Workshop","Open Workshop") else
                "menu" if label in ("Menu","Main menu","Map") else "note" if label in ("Notes","Explain") else
                "sensor" if label.startswith("Colour ") else None)
        while font.size(label)[0]>rect.width-(40 if symbol else 16) and font.get_height()>14:
            font=pygame.font.Font(None,font.get_height()-1)
        effective_style="aqua" if selected else style
        colour=(24,20,43) if effective_style in ("gold","aqua","green","red") and enabled else TEXT if enabled else (170,164,187)
        image=font.render(label,True,colour)
        if symbol:theme.icon(self.surface,symbol,(rect.x+18,rect.centery-2),colour,14)
        self.surface.blit(image,image.get_rect(center=(rect.centerx+(9 if symbol else 0),rect.centery-2+int(pressed)*2)))
        if selected:
            pygame.draw.rect(self.surface,TEAL,rect.inflate(-2,-2),2,border_radius=10)
        clipped=rect.clip(self.surface.get_clip())
        if clipped.width and clipped.height:
            index=len(self.buttons)
            if self.focus==index and enabled:
                pygame.draw.rect(self.surface,GOLD,rect.inflate(5,5),2,border_radius=12)
            self.buttons.append((clipped,action,enabled,label,tip))

    def slider(self,key,rect,value,low,high,setter,enabled=True):
        rect=pygame.Rect(rect)
        pygame.draw.rect(self.surface,INK,(rect.left,rect.centery-6,rect.width,12),border_radius=6)
        fraction=max(0,min(1,(value-low)/(high-low)))
        colour=TEAL if enabled else (135,125,153)
        pygame.draw.rect(self.surface,colour,(rect.left+2,rect.centery-4,max(1,(rect.width-4)*fraction),8),border_radius=4)
        knob=(int(rect.left+fraction*rect.width),rect.centery)
        pygame.draw.circle(self.surface,(28,53,77),(knob[0],knob[1]+3),11)
        pygame.draw.circle(self.surface,colour,knob,11)
        pygame.draw.circle(self.surface,(195,255,245),knob,10,2)
        if enabled:self.sliders[key]=(rect.inflate(12,14),low,high,setter,value)

    def apply_slider(self,key):
        if key in self.sliders:
            rect,low,high,setter,_=self.sliders[key]
            fraction=max(0,min(1,(self.mouse[0]-rect.left-6)/(rect.width-12)))
            setter(round(low+fraction*(high-low),3))

    def transform(self,position):
        width,height=self.window.get_size()
        return position[0]*self.WIDTH/width,position[1]*self.HEIGHT/height

    def resize(self,size):
        self.window=pygame.display.set_mode(size,pygame.RESIZABLE)
        self.game.settings["window"]=list(size)
        self.renderer.static_key=None

    def start_numeric(self,index):
        self.editing=[index,f"{self.game.gains()[index]:.2f}"]
        self.edit_paused=self.game.paused
        self.game.paused=True
        pygame.key.start_text_input()

    def close_numeric(self,apply=False):
        if apply:
            try:
                value=float(self.editing[1])
                if not math.isfinite(value) or not 0<=value<=(16,5,2,3)[self.editing[0]]:raise ValueError
            except ValueError:
                self.game.notify("Enter a value within the displayed range.")
                return
            self.game.change_gain(self.editing[0],value)
        self.editing=None
        self.game.paused=self.edit_paused
        pygame.key.stop_text_input()

    def ask_confirm(self,text,action):
        self.confirm_text,self.confirm_action=text,action
        self.game.open_panel(Scene.CONFIRM)

    def confirm(self):
        action=self.confirm_action
        self.game.close_panel()
        self.confirm_action=None
        if action:action()

    def focus_next(self,delta=1):
        enabled=[i for i,b in enumerate(self.buttons) if b[2]]
        if enabled:
            self.focus=enabled[(enabled.index(self.focus)+delta)%len(enabled)] if self.focus in enabled else enabled[0]

    def events(self,events):
        g=self.game
        for event in events:
            if event.type==pygame.QUIT:
                g.save(); self.quit=True
            elif event.type==pygame.VIDEORESIZE and not self.fullscreen:
                self.resize((max(800,event.w),max(600,event.h)))
            elif event.type in (getattr(pygame,"WINDOWFOCUSLOST",-1),getattr(pygame,"WINDOWMINIMIZED",-2)):
                if g.mode in (Scene.PLAYING,Scene.EXPERIMENT):g.paused=True
                self.dragging=None
            elif event.type==pygame.MOUSEMOTION:
                self.mouse=self.transform(event.pos)
                if self.dragging:self.apply_slider(self.dragging)
                elif g.practice and hasattr(self,"field") and self.field.collidepoint(self.mouse) and getattr(event,"buttons",(0,0,0))[2]:
                    self.renderer.camera.yaw+=event.rel[0]*.3
                    self.renderer.camera.elevation=max(25,min(75,self.renderer.camera.elevation+event.rel[1]*.2))
            elif event.type==pygame.MOUSEWHEEL:
                if g.practice and hasattr(self,"field") and self.field.collidepoint(self.mouse):
                    self.renderer.camera.zoom=max(.7,min(1.7,self.renderer.camera.zoom+event.y*.1))
                else:self.coach_scroll=max(0,min(self.max_scroll,self.coach_scroll-event.y*45))
            elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
                self.dragging=None
            elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                self.mouse=self.transform(event.pos)
                for key,(rect,*_) in self.sliders.items():
                    if rect.collidepoint(self.mouse):
                        self.dragging=key; self.active_slider=key; self.apply_slider(key); break
                else:
                    for index,(rect,action,enabled,_,tip) in reversed(list(enumerate(self.buttons))):
                        if rect.collidepoint(self.mouse):
                            self.focus=index
                            if enabled:
                                self.audio.play("click",g.settings)
                                action()
                                # Events queued in one frame cannot click controls
                                # belonging to a scene that has just disappeared.
                                self.buttons=[];self.sliders={}
                            elif tip:g.notify(tip)
                            break
            elif event.type==pygame.TEXTINPUT and self.editing:
                self.editing[1]=(self.editing[1]+event.text)[:12]
            elif event.type==pygame.KEYDOWN:
                if self.editing:
                    if event.key==pygame.K_ESCAPE:self.close_numeric()
                    elif event.key==pygame.K_RETURN:self.close_numeric(True)
                    elif event.key==pygame.K_BACKSPACE:self.editing[1]=self.editing[1][:-1]
                    elif event.key==pygame.K_a and event.mod&pygame.KMOD_CTRL:self.editing[1]=""
                    continue
                if event.key==pygame.K_F11:
                    if not self.fullscreen:
                        self.windowed=self.window.get_size()
                        self.window=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
                    else:self.resize(self.windowed)
                    self.fullscreen=not self.fullscreen
                    self.renderer.static_key=None
                elif event.key==pygame.K_TAB:self.focus_next(-1 if event.mod&pygame.KMOD_SHIFT else 1)
                elif event.key in (pygame.K_RETURN,pygame.K_SPACE) and 0<=self.focus<len(self.buttons):
                    if self.buttons[self.focus][2]:self.buttons[self.focus][1]();self.buttons=[]
                elif event.key==pygame.K_ESCAPE:
                    if g.mode==Scene.CONGRATS:g.notify("Your achievement is saved. Select Continue when ready.")
                    elif g.router.stack:g.close_panel()
                    elif g.mode in (Scene.PLAYING,Scene.EXPERIMENT):g.paused=not g.paused
                    elif g.mode==Scene.COACH:g.go_menu()
                elif event.key==pygame.K_SPACE and g.mode in (Scene.PLAYING,Scene.EXPERIMENT):g.paused=not g.paused
                elif event.key==pygame.K_PERIOD and g.paused:
                    if g.mode==Scene.PLAYING:g.tick(g.STEP)
                    elif g.mode==Scene.EXPERIMENT:
                        g.trial.tick()
                        if g.trial.done:g.finish_experiment()
                elif event.key in (pygame.K_PAGEUP,pygame.K_PAGEDOWN):
                    self.coach_scroll=max(0,min(self.max_scroll,self.coach_scroll+(-160 if event.key==pygame.K_PAGEUP else 160)))
                elif event.key in (pygame.K_LEFT,pygame.K_RIGHT) and self.sliders:
                    # Numeric fields provide exact control; arrows adjust the
                    # most recently used slider (or first editable one).
                    key=self.active_slider if self.active_slider in self.sliders else next(iter(self.sliders))
                    _,lo,hi,setter,value=self.sliders[key]
                    setter(max(lo,min(hi,value+(hi-lo)/100*(1 if event.key==pygame.K_RIGHT else -1))))
                elif g.mode in (Scene.COACH,Scene.READY,Scene.PLAYING):
                    if pygame.K_1<=event.key<=pygame.K_5:g.set_algorithm(event.key-pygame.K_1)
                    elif event.key==pygame.K_v:g.overlay=not g.overlay
                    elif event.key==pygame.K_h:self.show_why=not self.show_why
                    elif event.key in (pygame.K_LEFTBRACKET,pygame.K_RIGHTBRACKET):g.set_lead(g.lead+(-.05 if event.key==pygame.K_LEFTBRACKET else .05))

    def update(self,dt):
        self.wall_time+=dt
        self.profile["samples"]+=1
        self.profile["frame_ms"]+=(dt*1000-self.profile["frame_ms"])*.05
        task=self.game.runner.key(self.game.step) if self.game.step else "done"
        if task!=self.last_task:
            self.coach_scroll=0;self.show_why=False;self.last_task=task;self.focus=-1
        if self.last_scene!=self.game.mode:
            if self.last_scene:self.scroll_positions[self.last_scene]=self.coach_scroll
            self.coach_scroll=self.scroll_positions.get(self.game.mode,0)
            self.focus=-1;self.dragging=None;self.last_scene=self.game.mode
        # Audio follows domain events, never changes physics or assessment.
        events=list(self.game.events)
        fresh=events if self.event_cursor is None else events[next((i+1 for i,e in enumerate(events) if e is self.event_cursor),len(events)):]
        for event in fresh:
            cue={"shot":"shot","hit":"hit","step_completed":"win"}.get(event.kind)
            if cue:self.audio.play(cue,self.game.settings)
        if events:self.event_cursor=events[-1]

    def layout(self):
        actual=self.window.get_size()
        size=(max(1000,actual[0]),max(700,actual[1]))
        if self.surface.get_size()!=size:
            self.surface=pygame.Surface(size)
        self.WIDTH,self.HEIGHT=size
        self.rail=pygame.Rect(self.WIDTH-372,128,352,self.HEIGHT-204)
        self.field=pygame.Rect(20,128,self.WIDTH-410,self.HEIGHT-352)
        self.instruments=pygame.Rect(20,self.HEIGHT-214,self.field.width,138)

    def draw(self):
        self.layout()
        theme.set_contrast(self.game.settings["high_contrast"])
        self.buttons=[];self.sliders={}
        self.surface.fill(BG)
        if self.game.mode==Scene.TITLE:self.draw_title()
        else:
            self.draw_header();self.draw_battlefield();self.draw_instruments();self.draw_coach();self.draw_transport()
            if self.game.mode in (Scene.CONGRATS,Scene.SHOP,Scene.MAP,Scene.NOTEBOOK,Scene.OPTIONS,Scene.CONFIRM,Scene.VICTORY,Scene.RESULT):
                self.buttons=[];self.sliders={}
                shade=pygame.Surface(self.surface.get_size(),pygame.SRCALPHA);shade.fill((13,8,35,170));self.surface.blit(shade,(0,0))
                getattr(self,"draw_"+str(self.game.mode))()
        if self.algorithm_popup and self.game.mode in (Scene.COACH,Scene.READY,Scene.PLAYING):self.draw_algorithms()
        if self.editing:self.draw_numeric()
        if self.game.toast_time>0:
            # Reserved header band: never covers gain or transport controls.
            pygame.draw.rect(self.surface,(56,54,91),(20,98,self.WIDTH-40,25),border_radius=5)
            self.text(self.game.toast,30,100,16,GOLD)
        elif self.game.save_note:
            self.text(self.game.save_note,24,101,15,GOLD)
        if self.focus>=len(self.buttons):self.focus=-1
        self.window.fill(BG)
        if self.window.get_size()==self.surface.get_size():self.window.blit(self.surface,(0,0))
        else:self.window.blit(pygame.transform.smoothscale(self.surface,self.window.get_size()),(0,0))
        pygame.display.flip()

    def draw_header(self):
        g=self.game
        self.text("LEAD THE TARGET",24,18,32,GOLD,True,shadow=True)
        self.text(g.lesson.title,360,22,22,TEXT,True)
        self.text(f"{g.currency}  COINS",self.WIDTH-180,21,23,GOLD,True)
        for i in range(8):
            done=all(f"{i}:{s.id}" in g.learning for s in STEPS[i])
            star(self.surface,(40+i*32,75),12,GOLD if done else (104,91,141))
        self.text("FREE PLAY - no mastery" if g.practice else "LEARN  >  EXPERIMENT  >  DEFEND",305,65,17,TEAL,True)
        x=self.WIDTH-322
        self.button((x,61,88,32),"Map",lambda:g.open_panel(Scene.MAP),"purple")
        self.button((x+98,61,88,32),"Notes",lambda:g.open_panel(Scene.NOTEBOOK))
        self.button((x+196,61,106,32),"Options",lambda:g.open_panel(Scene.OPTIONS))

    def draw_title(self):
        g=self.game
        left=pygame.Rect(32,80,420,self.HEIGHT-150)
        right=pygame.Rect(475,100,self.WIDTH-500,self.HEIGHT-210)
        panel(self.surface,left,foliage=True)
        self.text("CONTROL QUEST",62,115,25,TEAL,True)
        self.text("LEAD THE",62,163,51,GOLD,True,shadow=True)
        self.text("TARGET",62,216,59,GOLD,True,shadow=True)
        self.wrap("Think ahead. Build a smarter tower.",62,292,350,23,TEXT,True)
        self.wrap("Predict moving targets, unlock sensors and tune a tracking motor. Each skill is earned through a measured experiment.",62,361,350,20)
        y=max(500,self.HEIGHT-260)
        self.button((62,y,360,52),"Continue your quest" if g.saved else "Start your quest",lambda:g.start_campaign(),"gold")
        self.button((62,y+64,174,44),"New campaign",lambda:self.ask_confirm("Start a new campaign? Your existing save is backed up before replacement.",lambda:g.start_campaign(True)),"purple")
        self.button((248,y+64,174,44),"Free play",lambda:g.enter_sandbox(0),"aqua")
        self.renderer.draw(self.surface,right,g,preview=True)
        self.text("AIM FOR THE FUTURE",right.left+30,75,28,TEXT,True,shadow=True)
        self.wrap("Eight skills. Real physics. One evolving defense.",right.left+30,right.bottom+18,right.width-40,22,TEAL,True)
        self.text("Tab: focus  |  Enter: activate  |  F11: fullscreen",38,self.HEIGHT-43,17,MUTED)
        # New-campaign confirmation also works while the title is behind it.
        if g.mode==Scene.CONFIRM:
            self.buttons=[];self.draw_confirm()

    def draw_battlefield(self):
        g=self.game
        panel(self.surface,self.field)
        self.button((self.field.x+14,self.field.y+12,235,38),"Aim: "+g.strategies[g.algorithm].name,lambda:setattr(self,"algorithm_popup",not self.algorithm_popup),"aqua")
        self.button((self.field.right-166,self.field.y+12,150,38),"Colour "+("ON" if g.colour_enabled and g.upgrades["colour"] else "OFF"),g.toggle_colour,"green",bool(g.upgrades["colour"]),tip="Install the colour sensor in Workshop.")
        viewport=pygame.Rect(self.field.x+5,self.field.y+58,self.field.width-10,self.field.height-64)
        trial=g.trial if g.mode in (Scene.EXPERIMENT,Scene.CONGRATS,Scene.COACH) and g.trial else None
        if g.mode==Scene.COACH and g.step and g.step.scenario and g.step.kind=="trial":
            key=(g.step.scenario,g.algorithm,g.lead,g.gains(),bool(g.upgrades["colour"] and g.colour_enabled))
            if key!=self.preview_key:
                self.preview=Experiment(key[0],g.strategies,*key[1:])
                self.preview_key=key
            trial=self.preview
        self.renderer.draw(self.surface,viewport,g,trial,preview=g.mode not in (Scene.PLAYING,Scene.EXPERIMENT))
        if g.mode in (Scene.PLAYING,Scene.READY):
            self.text(f"BASE {max(0,g.health)}/16  |  {g.hits}/{g.shots} hits  |  {100*g.hits/max(1,g.shots):.0f}%",self.field.x+16,self.field.bottom-30,18,TEXT,True)
        elif g.mode==Scene.EXPERIMENT:
            self.text(f"MEASURING {g.trial.time:.1f} / {g.trial.duration:.0f} s"+("  PAUSED" if g.paused else ""),self.field.x+16,self.field.bottom-30,18,GOLD,True)
        else:self.text("CYAN: lead  |  WHITE: barrel  |  AMBER: shell",self.field.x+16,self.field.bottom-30,17,TEXT)
        if (trial and trial.tracking) or (g.controlled and g.mode==Scene.PLAYING):
            graph=pygame.Rect(self.field.right-265,self.field.y+66,245,133)
            pygame.draw.rect(self.surface,INK,graph,border_radius=8)
            raw=trial.samples[-360:] if trial and trial.tracking else list(g.history)
            history=[(t,s,r) for t,s,r,_,_ in raw]
            self.plot((graph.x+10,graph.y+27,225,46),history)
            self.text("ERROR (deg) / AIM / BARREL",graph.x+10,graph.y+5,14,GOLD,True)
            if len(raw)>1:
                for index,colour in ((3,GOLD),(4,TEXT)):
                    points=[(graph.x+10+225*(1-(raw[-1][0]-row[0])/12),graph.y+100-math.degrees(row[index])/180*20) for row in raw]
                    old=self.surface.get_clip();self.surface.set_clip(graph)
                    pygame.draw.lines(self.surface,colour,False,points,2);self.surface.set_clip(old)
            self.text("Aim gold / barrel white; +/-180 deg",graph.x+10,graph.bottom-18,12,MUTED)

    def draw_algorithms(self):
        x,y=self.field.x+14,self.field.y+54
        panel(self.surface,(x,y,310,255))
        for i,strategy in enumerate(self.game.strategies):
            unlocked=i<=self.game.unlock
            label=f"{i+1}  {strategy.name}" if unlocked else f"Locked: lesson {max(3,i+1)}"
            self.button((x+12,y+12+i*47,286,40),label,lambda n=i:self.choose_algorithm(n),"aqua",unlocked,selected=i==self.game.algorithm,tip="Complete earlier lessons or use Free play.")

    def choose_algorithm(self,index):
        self.game.set_algorithm(index);self.algorithm_popup=False

    def gain_enabled(self,index):
        g=self.game
        if g.practice:return g.stage>=5
        if g.mode in (Scene.EXPERIMENT,Scene.CONGRATS):return False
        if g.step and g.step.kind=="wave":return g.stage>=5 and (index<3 or g.stage>=7)
        return bool(g.step and g.step.scenario==("p_tune","i_tune","d_tune","f_tune")[index])

    def draw_instruments(self):
        g=self.game;r=self.instruments
        panel(self.surface,r)
        tracking=g.stage>=5
        if not tracking:
            self.text("LEAD TIME",r.x+18,r.y+14,20,GOLD,True)
            self.text(f"{g.lead:.2f} s",r.x+170,r.y+14,22,TEXT,True)
            self.slider("lead",(r.x+276,r.y+16,r.width-302,24),g.lead,0,2,g.set_lead,g.algorithm==1 and g.mode!=Scene.EXPERIMENT)
            self.wrap(g.lesson.formula,r.x+18,r.y+59,r.width-36,18,TEAL)
            self.text("Edit [ ] or drag. The aim point updates; Run tests your prediction.",r.x+18,r.bottom-29,16,MUTED)
            return
        self.text("PIDF MOTOR",r.x+16,r.y+8,19,GOLD,True)
        trial=g.trial if g.trial and g.trial.tracking and g.mode in (Scene.EXPERIMENT,Scene.COACH,Scene.CONGRATS) else None
        gains=calibration_gains(g.step.scenario,g.gains()) if g.step and g.step.kind=="trial" else g.gains()
        sample=trial.tower.controller.sample if trial else g.tower.controller.sample
        width=(r.width-32)/4
        for i,(name,value,maximum) in enumerate(zip("PIDF",gains,(16,5,2,3))):
            x=r.x+16+i*width
            self.text(name,x,r.y+35,21,TERMS[i],True)
            self.button((x+32,r.y+28,int(width)-46,33),f"{value:.2f}",lambda n=i:self.start_numeric(n),enabled=self.gain_enabled(i),tip="Only the current experimental term is editable.")
            self.slider("pidf"[i],(x+5,r.y+65,width-22,22),value,0,maximum,lambda v,n=i:g.change_gain(n,v),self.gain_enabled(i))
            term=math.degrees((sample.p,sample.i,sample.d,sample.f)[i])
            self.text(f"{term:+.1f} deg/s",x+3,r.y+93,17,TERMS[i])
            origin=x+width/2
            pygame.draw.line(self.surface,EDGE,(origin,r.y+117),(origin,r.y+129),1)
            length=max(-width/2+15,min(width/2-15,term/180*(width/2-15)))
            pygame.draw.line(self.surface,TERMS[i],(origin,r.y+123),(origin+length,r.y+123),4)
        saturated=abs(sample.requested-sample.output)>.01
        rate=trial.tower.rate if trial else g.tower.rate
        self.text(f"Error {math.degrees(sample.error):+.1f} deg   request {math.degrees(sample.requested):+.0f} / limit {math.degrees(sample.output):+.0f} / motor {math.degrees(rate):+.0f} deg/s"+("  SATURATED" if saturated else ""),r.x+180,r.y+9,15,RED if saturated else MUTED)

    def draw_coach(self):
        g=self.game;r=self.rail
        panel(self.surface,r,accent=True)
        done=sum(f"{g.stage}:{s.id}" in g.learning for s in g.runner.steps)
        total=len(g.runner.steps)
        self.text("FREE PLAY" if g.practice else f"YOUR QUEST  {min(total,done+1)} / {total}",r.x+20,r.y+27,20,GOLD,True)
        for i in range(total):
            colour=GREEN if i<done else GOLD if i==done else (105,92,143)
            pygame.draw.rect(self.surface,colour,(r.x+20+i*(r.width-40)/total,r.y+58,(r.width-48)/total,7),border_radius=3)
        body=pygame.Rect(r.x+16,r.y+82,r.width-32,r.height-180)
        old=self.surface.get_clip();self.surface.set_clip(body)
        y=body.y-self.coach_scroll
        step=g.step
        if g.mode==Scene.EXPERIMENT and g.replay_trial:
            y=self.wrap("REPLAY: "+g.replay_title,body.x,y,body.width,27,TEXT,True)
            y=self.wrap("Watch your measured solution again. No evidence or rewards change. At the end you return to the notebook or congratulations screen.",body.x,y+20,body.width,21,TEAL)
        elif g.practice:
            y=self.wrap("Defend the road",body.x,y,body.width,28,TEXT,True)
            y=self.wrap(g.lesson.challenge,body.x,y+15,body.width,21)
            y=self.wrap("All algorithms are unlocked. Experiment freely; campaign mastery and credits stay safe.",body.x,y+18,body.width,19,TEAL)
            if g.mode==Scene.PLAYING:
                y=self.wrap(g.wait_reason,body.x,y+22,body.width,19,GOLD)
                self.wrap(f"Resolved: {sum(s.outcome!='pending' for s in g.records)} / {g.shots} shots",body.x,y+15,body.width,18)
        elif step:
            y=self.wrap(step.title,body.x,y,body.width,28,TEXT,True)
            y=self.wrap(step.task,body.x,y+16,body.width,21)
            if step.kind=="choice":
                for answer in step.options:
                    self.button((body.x,y+12,body.width,49),answer,lambda v=answer:g.answer(v),"aqua")
                    y+=61
            elif step.kind=="trial":
                y=self.wrap("LAB: fixed equipment. Only the current variable changes.",body.x,y+20,body.width,18,TEAL)
                if step.scenario.startswith(("p_","i_","d_","f_")):
                    before=step.scenario.replace("tune","base")
                    baseline=g.runner.evidence_for(before)
                    if baseline:y=self.wrap(f"Baseline: RMS {baseline.get('rms_error',0):.2f} deg; steady {baseline.get('steady_error',0):.2f}; overshoot {baseline.get('overshoot',0):.2f}.",body.x,y+12,body.width,18,GOLD)
            elif step.kind=="wave" and g.mode==Scene.PLAYING:
                y=self.wrap("TOWER: "+g.wait_reason,body.x,y+20,body.width,19,GOLD)
                y=self.wrap(f"Tank {g.spawned}/{g.lesson.count}. Base {max(0,g.health)}/16. All pending shots resolve before the report.",body.x,y+12,body.width,18,TEAL)
            if g.runner.feedback:
                y=self.wrap(g.runner.feedback,body.x,y+22,body.width,19,RED)
            if self.show_why:
                y=self.wrap("WHY IT WORKS",body.x,y+22,body.width,19,GOLD,True)
                y=self.wrap(step.why,body.x,y+8,body.width,20)
            if self.advanced:
                y=self.wrap("ALGORITHM INSPECTOR",body.x,y+22,body.width,18,GOLD,True)
                branch=g.trial.metrics.branch if g.trial and not g.trial.tracking else g.solution.branch if g.solution else "Waiting for observation"
                for line in g.strategies[g.algorithm].pseudocode:
                    executing=("RED" in branch and "RED" in line) or ("GOLD" in branch and "GOLD" in line) or ("NO COLOUR" in branch and "None" in line)
                    y=self.wrap(("> " if executing else "  ")+line,body.x,y+5,body.width,17,TEAL if executing else MUTED)
                y=self.wrap(branch,body.x,y+12,body.width,18,GOLD)
        else:y=self.wrap("Skills complete. Your next mission awaits.",body.x,y,body.width,25,TEXT,True)
        self.max_scroll=max(0,y+self.coach_scroll-body.bottom+18)
        self.coach_scroll=min(self.coach_scroll,self.max_scroll)
        self.surface.set_clip(old)
        if self.max_scroll:
            self.text("Scroll / PgDn for more",r.x+20,r.bottom-96,15,MUTED)
        y=r.bottom-76
        if g.mode==Scene.EXPERIMENT:
            self.button((r.x+18,y,r.width-36,48),"Resume trial" if g.paused else "Pause trial",lambda:setattr(g,"paused",not g.paused),"gold")
        elif g.mode==Scene.PLAYING:
            self.button((r.x+18,y,r.width-36,48),"Resume defense" if g.paused else "Pause defense",lambda:setattr(g,"paused",not g.paused),"gold")
        elif g.practice:
            self.button((r.x+18,y,r.width-36,48),"Launch wave",g.begin_wave,"gold")
        elif step and step.kind=="trial":self.button((r.x+18,y,r.width-36,48),"Run experiment",g.run_experiment,"gold")
        elif step and step.kind=="wave":self.button((r.x+18,y,r.width-36,48),"Launch defense",g.begin_wave,"gold")
        elif step and step.kind=="purchase":
            self.button((r.x+18,y,r.width-36,48),"Verify installed sensor" if g.upgrades["colour"] else "Open Workshop",g.verify_sensor if g.upgrades["colour"] else g.open_shop,"gold")
        else:
            self.button((r.x+18,y,150,44),"Hint",self.hint,"aqua")
            self.button((r.x+178,y,156,44),"Why?",lambda:setattr(self,"show_why",not self.show_why),"purple")

    def hint(self):
        if self.game.step:self.game.runner.feedback=self.game.step.hint

    def draw_transport(self):
        g=self.game;y=self.HEIGHT-58
        self.button((20,y,110,40),"Menu",lambda:self.ask_confirm("Return to the menu? An active defense restarts; demonstrated skills and tuning are kept.",g.go_menu))
        self.button((140,y,110,40),"Workshop",g.open_shop,"purple",g.mode in (Scene.COACH,Scene.READY))
        self.button((260,y,90,40),"Hint",self.hint,"aqua")
        self.button((360,y,110,40),"Explain",lambda:setattr(self,"show_why",not self.show_why))
        self.button((480,y,105,40),"Inspect",lambda:setattr(self,"advanced",not self.advanced))
        self.button((595,y,95,40),f"{g.speed:g}x",self.cycle_speed)
        self.button((700,y,95,40),"Step [.]",self.single_step,enabled=g.paused and g.mode in (Scene.PLAYING,Scene.EXPERIMENT))
        self.button((805,y,110,40),"Camera",lambda:self.renderer.camera.reset())
        if self.WIDTH>1200:self.button((925,y,115,40),"Overlay [V]",lambda:setattr(g,"overlay",not g.overlay))

    def single_step(self):
        g=self.game
        if g.mode==Scene.EXPERIMENT:
            g.trial.tick()
            if g.trial.done:g.finish_experiment()
        elif g.mode==Scene.PLAYING:g.tick(g.STEP)

    def cycle_speed(self):
        values=(.25,.5,1,2)
        self.game.speed=values[(values.index(self.game.speed)+1)%4]

    def modal(self,title,subtitle="",height=550):
        rect=pygame.Rect(0,0,min(920,self.WIDTH-70),min(height,self.HEIGHT-90))
        rect.center=(self.WIDTH//2,self.HEIGHT//2)
        panel(self.surface,rect,foliage=True)
        self.text(title,rect.x+30,rect.y+24,34,GOLD,True,shadow=True)
        if subtitle:self.wrap(subtitle,rect.x+30,rect.y+75,rect.width-60,20)
        return rect

    def draw_congrats(self):
        g=self.game
        record=g.learning.get(g.runner.pending,{})
        r=self.modal("CONGRATULATIONS!",record.get("title","Lesson mastered"),590)
        for i in range(3):
            offset=0 if g.settings["reduced_motion"] else math.sin(self.wall_time*3+i)*3
            star(self.surface,(r.centerx+(i-1)*100,r.y+165+offset),42 if i==1 else 30)
        if not g.settings["reduced_motion"]:
            for i in range(16):
                x=r.x+30+(i*71)%max(1,r.width-60)
                y=r.y+135+(self.wall_time*30+i*29)%135
                pygame.draw.rect(self.surface,(GOLD,TEAL,GREEN)[i%3],(x,y,4,7))
        self.wrap(record.get("why","You demonstrated the skill and defended the base."),r.x+38,r.y+240,r.width-76,23,TEXT)
        evidence=record.get("evidence",{})
        if "answer" in evidence:summary="Your answer: "+str(evidence["answer"])
        elif "rms_error" in evidence:
            kind=evidence.get("kind","")
            term=kind[0] if kind else "p"
            metric={"p":"rms_error","i":"steady_error","d":"overshoot","f":"steady_error"}.get(term,"rms_error")
            baseline=g.runner.evidence_for(term+"_base")
            if kind.endswith("tune") and baseline.get(metric,0)>0:
                before,after=baseline[metric],evidence[metric]
                summary=f"{metric.replace('_',' ').title()}: {before:.2f} -> {after:.2f} deg. {100*(1-after/before):.0f}% improvement measured!"
            else:summary=(f"Measured RMS: {evidence['rms_error']:.2f} deg   |   steady error: {evidence['steady_error']:.2f} deg   |   overshoot: {evidence['overshoot']:.2f} deg")
        elif "hits" in evidence:summary=f"Field evidence: {evidence['hits']} hits / {evidence['shots']} shots"
        elif "miss_distance" in evidence:summary=f"{'HIT' if evidence.get('hit') else 'BASELINE MISS'}  |  separation {evidence['miss_distance']:.1f} px  |  {evidence.get('branch','')}"
        else:summary="Verified sensor observation: "+str(evidence.get("observed","skill complete"))
        self.wrap(summary,r.x+38,r.y+370,r.width-76,20,TEAL,True)
        self.text(("+10 coins  |  " if record.get("rewarded") else "")+"Skill recorded  |  Continue when you are ready",r.x+38,r.bottom-125,20,GOLD,True)
        self.button((r.x+36,r.bottom-72,225,47),"Replay experiment",g.replay,"aqua",g.last_trial is not None)
        self.button((r.right-261,r.bottom-72,225,47),"Continue",g.continue_learning,"gold")

    def draw_shop(self):
        g=self.game;r=self.modal("WORKSHOP",f"{g.currency} coins. Tasks earn 10; field kills earn 8. Calibration equipment stays fixed.",640)
        card_w=(r.width-80)//3
        for i,(key,(name,prices,description)) in enumerate(UPGRADES.items()):
            x=r.x+24+(i%3)*(card_w+16);y=r.y+130+(i//3)*198
            pygame.draw.rect(self.surface,INK,(x,y,card_w,182),border_radius=12)
            star(self.surface,(x+card_w/2,y+34),22,(TEAL,GREEN,GOLD,BLUE,TERMS[3],RED)[i])
            self.text(name,x+12,y+65,20,TEXT,True)
            self.wrap(description,x+12,y+92,card_w-24,16,MUTED)
            level=g.upgrades[key]
            allowed=g.practice or key=="colour" or bool(g.step and g.step.kind=="wave")
            label="Installed MAX" if level==len(prices) else f"Buy {prices[level]} coins"
            self.button((x+10,y+140,card_w-20,34),label,lambda k=key:g.buy(k),"gold",level<len(prices) and g.currency>=prices[level] and allowed,
                        tip="Field upgrades apply after guided calibration. The colour sensor can be installed now.")
        self.button((r.x+25,r.bottom-57,250,38),"Colour input "+("ON" if g.colour_enabled and g.upgrades["colour"] else "OFF"),g.toggle_colour,"green",bool(g.upgrades["colour"]))
        self.button((r.right-235,r.bottom-57,210,38),"Return to task",g.close_panel,"aqua")

    def draw_map(self):
        g=self.game;r=self.modal("YOUR SKILL MAP","Stars mark demonstrated skills. Free play never overwrites campaign mastery.",570)
        w=(r.width-70)/4
        for i,lesson in enumerate(LESSONS):
            x=r.x+20+(i%4)*(w+9);y=r.y+132+(i//4)*160
            count=sum(f"{i}:{s.id}" in g.learning for s in STEPS[i])
            pygame.draw.rect(self.surface,INK,(x,y,w,145),border_radius=10)
            star(self.surface,(x+26,y+27),17,GOLD if count==len(STEPS[i]) else EDGE)
            self.text(f"{i+1}",x+58,y+12,28,GOLD,True)
            self.wrap(lesson.title.split("/",1)[1].strip(),x+10,y+56,w-20,18,TEXT,True)
            self.button((x+10,y+103,w-20,33),f"Free play {i+1}",lambda n=i:g.enter_sandbox(n),"aqua")
        self.button((r.x+25,r.bottom-62,210,42),"Guided campaign",lambda:g.start_campaign(),"gold")
        self.button((r.right-235,r.bottom-62,210,42),"Return",g.close_panel)

    def draw_notebook(self):
        g=self.game;r=self.modal("FIELD NOTEBOOK","Your formulas, demonstrated skills and measured results. Scroll / PgDn for more.",620)
        body=pygame.Rect(r.x+28,r.y+125,r.width-56,r.height-205)
        self.surface.set_clip(body);y=body.y-self.coach_scroll
        if not g.learning:y=self.wrap("Your first discovery belongs here. Complete a guided task to record it.",body.x,y,body.width,23,TEXT)
        for key,record in g.learning.items():
            y=self.wrap(f"{int(key.split(':')[0])+1}  /  {record.get('title','Skill')}",body.x,y,body.width,23,GOLD,True)
            y=self.wrap(record.get("why",""),body.x,y+6,body.width,19,TEXT)
            evidence=record.get("evidence",{})
            if "rms_error" in evidence:y=self.wrap(f"Measured: RMS {evidence['rms_error']:.2f} deg, steady {evidence['steady_error']:.2f} deg, overshoot {evidence['overshoot']:.2f} deg.",body.x,y+5,body.width,18,TEAL)
            if "kind" in evidence:
                self.button((body.x,y+8,220,36),"Replay this experiment",lambda k=key:g.review_record(k),"aqua")
                y+=52
            y+=26
        self.max_scroll=max(0,y+self.coach_scroll-body.bottom)
        self.surface.set_clip(None)
        self.button((r.x+28,r.bottom-61,230,42),"Replay latest trial",g.replay,"aqua",g.last_trial is not None)
        self.button((r.right-258,r.bottom-61,230,42),"Return",g.close_panel,"gold")

    def toggle_setting(self,key):
        self.game.settings[key]=not self.game.settings[key]
        self.game.save()

    def draw_options(self):
        g=self.game;r=self.modal("OPTIONS","Tab cycles controls. Enter activates. Use arrows for sliders; click gain values for exact entry.",570)
        labels=(("muted","Sound muted"),("reduced_motion","Reduced motion"),("large_text","Larger text"),("high_contrast","High contrast"))
        for i,(key,label) in enumerate(labels):
            y=r.y+145+i*66
            self.text(label,r.x+35,y+8,23,TEXT,True)
            self.button((r.right-225,y,185,44),"ON" if g.settings[key] else "OFF",lambda k=key:self.toggle_setting(k),"green",selected=g.settings[key])
        self.text("Volume",r.x+35,r.y+424,22,TEXT,True)
        self.slider("volume",(r.x+200,r.y+426,r.width-250,24),g.settings["volume"],0,1,lambda v:self.set_volume(v))
        self.button((r.x+35,r.bottom-62,260,44),"Reset campaign...",lambda:self.ask_confirm("Start a new campaign? The current save is backed up before replacement.",lambda:g.start_campaign(True)),"red")
        self.button((r.right-245,r.bottom-62,210,44),"Return",g.close_panel,"gold")

    def set_volume(self,value):
        self.game.settings["volume"]=value

    def draw_confirm(self):
        r=self.modal("ARE YOU SURE?",self.confirm_text,330)
        self.button((r.x+30,r.bottom-80,230,50),"Cancel",self.game.close_panel,"aqua")
        self.button((r.right-260,r.bottom-80,230,50),"Confirm",self.confirm,"gold")

    def draw_result(self):
        g=self.game;r=self.modal("FIELD SECURED!" if g.success else "TRY ANOTHER STRATEGY",g.result_hint,470)
        for i,(label,value) in enumerate((("HITS / SHOTS",f"{g.hits} / {g.shots}"),("ACCURACY",f"{100*g.hits/max(1,g.shots):.0f}%"),("TANKS STOPPED",f"{g.kills}/{g.lesson.count}"))):
            x=r.x+35+i*(r.width-70)/3
            self.text(label,x,r.y+170,19,MUTED,True);self.text(value,x,r.y+207,38,(TEAL,GOLD,GREEN)[i],True)
        self.wrap(g.lesson.challenge,r.x+35,r.y+288,r.width-70,21,TEXT)
        self.button((r.x+35,r.bottom-70,220,46),"Replay wave",g.retry,"gold")
        self.button((r.right-255,r.bottom-70,220,46),"Skill map",lambda:g.open_panel(Scene.MAP),"aqua")

    def draw_victory(self):
        r=self.modal("QUEST COMPLETE!","You demonstrated prediction, sensing, P, I, D and feedforward, then defended the field.",520)
        for i in range(3):star(self.surface,(r.centerx+(i-1)*105,r.y+205),48 if i==1 else 36)
        self.wrap("Your notebook keeps the evidence. Try new combinations in Free play, or replay a measured experiment to strengthen a skill.",r.x+40,r.y+310,r.width-80,24,TEXT)
        self.button((r.x+35,r.bottom-73,240,47),"Explore free play",lambda:self.game.enter_sandbox(7),"aqua")
        self.button((r.right-275,r.bottom-73,240,47),"Main menu",self.game.go_menu,"gold")

    def draw_numeric(self):
        self.buttons=[];self.sliders={}
        r=self.modal("EXACT GAIN",f"Set {'PIDF'[self.editing[0]]}. Range 0 to {(16,5,2,3)[self.editing[0]]}. Ctrl+A clears the field.",340)
        pygame.draw.rect(self.surface,INK,(r.x+35,r.y+145,r.width-70,60),border_radius=8)
        self.text(self.editing[1]+"|",r.x+50,r.y+158,29,TEAL,True)
        self.button((r.x+35,r.bottom-70,200,45),"Cancel",lambda:self.close_numeric(),"aqua")
        self.button((r.right-235,r.bottom-70,200,45),"Apply",lambda:self.close_numeric(True),"gold")

    def plot(self,rect,history):
        rect=pygame.Rect(rect)
        pygame.draw.line(self.surface,EDGE,(rect.x,rect.centery),(rect.right,rect.centery),1)
        if len(history)<2:return
        peak=max(15,max(abs(math.degrees(s.error)) for _,s,_ in history))
        end=history[-1][0]
        points=[(rect.x+rect.width*(1-(end-t)/12),rect.centery-math.degrees(s.error)/peak*rect.height/2) for t,s,_ in history]
        clipped=self.surface.get_clip();self.surface.set_clip(rect)
        pygame.draw.lines(self.surface,TEAL,False,points,2);self.surface.set_clip(clipped)
        self.text(f"+/-{peak:.0f}   -12s > now",rect.x,rect.bottom-15,13,MUTED)
