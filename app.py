"""Panda3D application orchestration. Pure game rules live in separate modules."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from panda3d.core import ClockObject, TextNode, Filename, loadPrcFileData
from direct.showbase.ShowBase import ShowBase
from campaign import Campaign
from display import DisplayManager
from domain import Scene
from game import Game
from profile_store import load, save, DEFAULTS
from scene3d import Battlefield
from ui import Interface
from audio import Audio


class LeadTheTarget(ShowBase):
    def __init__(self,offscreen=False,preview=False,resolution=None):
        profile,note=load() if not preview else ({'campaign':{},'academy':{},'settings':deepcopy(DEFAULTS),'records':{}},'')
        self.prefs={**DEFAULTS,**profile.get('settings',{})}
        if resolution:self.prefs['resolution']=list(resolution)
        w,h=self.prefs['resolution']
        loadPrcFileData('game',f'window-title Lead the Target | Fortress Control\nwin-size {w} {h}\nwin-fixed-size false\nsync-video {str(self.prefs["vsync"]).lower()}\nframebuffer-multisample 1\nmultisamples 2\ntextures-power-2 none\nnotify-level warning\naudio-library-name {"null" if offscreen else "p3openal_audio"}\n')
        if offscreen:loadPrcFileData('verification','window-type offscreen\nload-display p3tinydisplay\ntextures-power-2 up\n')
        super().__init__(windowType='offscreen' if offscreen else None)
        if not self.win:raise RuntimeError('Panda3D could not open a graphics window.')
        self.preview=preview;self.offscreen=offscreen;self.save_note=note;self.notice=''
        fonts=Path(__file__).resolve().parent/'assets'/'fonts'
        self.font=self.loader.loadFont(Filename.fromOsSpecific(str(fonts/'Barlow-Regular.ttf')).getFullpath())
        self.font_bold=self.loader.loadFont(Filename.fromOsSpecific(str(fonts/'Barlow-SemiBold.ttf')).getFullpath())
        self.campaign=Campaign(profile.get('campaign'))
        self.academy=Game(profile.get('academy',{}),persist=False)
        self.records=profile.get('records',{})
        self.screen='title';self.previous_screen='title';self.map_page=(self.campaign.level-1)//10
        self.building=False;self.build_kind='standard';self.build_pad=None
        self.speed=1;self.recovery_count=0;self.contract=None
        self.audio=Audio(self)
        self.display=DisplayManager(self,self.prefs,offscreen)
        if not offscreen:self.display.request()
        self.scene=Battlefield(self);self.scene.compact=self.prefs['compact'];self.scene.resize()
        self.ui=Interface(self)
        self.last_scene=None;self.last_academy_mode=None;self.campaign_settled=False
        self.accept('escape',self.back);self.accept('space',self.pause_key)
        self.accept('c',self.compact_key);self.accept('tab',self.ui.focus_next);self.accept('enter',self.enter_key)
        self.accept('[',lambda:self.adjust_lead(-.05));self.accept(']',lambda:self.adjust_lead(.05))
        self.accept('mouse1',self.pick);self.accept('wheel_up',lambda:self.zoom_camera(1.08))
        self.accept('wheel_down',lambda:self.zoom_camera(1/1.08))
        self.accept('arrow_left',lambda:self.orbit(-.1));self.accept('arrow_right',lambda:self.orbit(.1))
        self.accept('window-event',self.on_window)
        self.taskMgr.add(self.frame,'game-update')
        self.ui.refresh();self.sync_scene()

    def save_profile(self):
        if self.preview:return True
        prefs=self.display.pending if self.display.pending is not None else self.prefs
        profile={'schema':3,'campaign':self.campaign.snapshot(),'academy':self.academy.snapshot(),
                 'settings':deepcopy(prefs),'records':self.records}
        ok=save(profile)
        if not ok:self.save_note='Could not save. Check write permissions; progress remains in this session.'
        return ok

    def navigate(self,screen):
        if self.display.pending is not None:self.display.revert()
        self.campaign.paused=True;self.academy.paused=True
        self.screen=screen;self.notice='';self.building=False
        self.save_profile()

    def enter_campaign(self,number=None):
        c=self.campaign
        if number is not None and number!=c.level:
            c.level=number;c.reset_encounter()
        self.screen='campaign';self.scene.clear_units();self.campaign.paused=False;self.notice=''
        self.save_profile()

    def enter_academy(self,stage):
        g=self.academy
        g.practice=False;g.stage=stage;g.prepare_stage()
        self.screen='academy';self.scene.clear_units();self.notice=''
        self.prepare_task();self.save_profile()

    def prepare_task(self):
        g=self.academy
        if g.mode==Scene.COACH and g.step and g.step.scenario=='fixed':g.set_algorithm(1)

    def change_map(self,delta):self.map_page=max(0,min(9,self.map_page+delta))

    def open_options(self):
        if self.screen=='options':return
        self.previous_screen=self.screen;self.navigate('options')

    def close_options(self):
        if self.display.pending is not None:self.display.revert()
        self.screen=self.previous_screen;self.save_profile()

    def apply_display(self,chosen):
        self.display.apply(chosen);self.ui.signature=None

    def confirm_display(self):self.display.confirm();self.ui.signature=None;self.save_profile()

    def revert_display(self):self.display.revert();self.ui.signature=None

    def toggle_pref(self,key):
        self.prefs[key]=not self.prefs[key]
        if key=='vsync':self.display.configure_clock()
        if key=='compact':self.scene.compact=self.prefs[key];self.scene.resize()
        self.ui.signature=None;self.save_profile()

    def toggle_compact(self):self.toggle_pref('compact')

    def compact_key(self):
        if not self.ui.editing():self.toggle_compact()

    def pause_key(self):
        if not self.ui.editing():self.launch_or_pause()

    def enter_key(self):
        if not self.ui.editing():self.ui.activate_focus()

    def launch_or_pause(self):
        if self.screen=='campaign':
            c=self.campaign
            if c.finished:return
            if c.running:c.paused=not c.paused
            else:c.start();self.campaign_settled=False;self.building=False;self.ui.signature=None
        elif self.screen=='academy':self.academy.paused=not self.academy.paused

    def next_encounter(self):
        if self.campaign.level==100:self.navigate('map');return
        self.campaign.next_level();self.campaign_settled=False;self.save_profile()

    def replay_encounter(self):self.campaign.reset_encounter();self.campaign_settled=False;self.save_profile()

    def relocate(self):
        if self.campaign.relocate():
            self.scene.clear_units();self.screen='campaign';self.building=False;self.campaign_settled=False;self.save_profile()

    def toggle_build(self):self.building=not self.building

    def choose_build(self,kind):self.build_kind=kind

    def pick(self):
        if self.screen!='campaign' or self.campaign.finished or self.display.pending is not None or self.ui.pointer_on_ui():return
        if not self.mouseWatcherNode.hasMouse():return
        pad=self.scene.pick_pad(self.mouseWatcherNode.getMouse())
        if pad is None:return
        self.build_pad=pad
        tower=next((t for t in self.campaign.towers if t.pad==pad),None)
        if tower:self.campaign.selected_id=tower.id;self.building=False
        elif self.building:
            if self.campaign.build(self.build_kind,pad):self.building=False
        else:self.campaign.message='Empty pad selected. Choose Build towers to deploy here.'
        self.save_profile()

    def upgrade(self):self.campaign.upgrade();self.save_profile()

    def sell(self):
        if self.campaign.sell():self.scene.clear_units()
        self.save_profile()

    def set_priority(self,value):
        if self.campaign.selected:self.campaign.selected.priority=value

    def copy_tuning(self):self.campaign.copy_configuration();self.save_profile()

    def set_algorithm(self,index):
        if self.screen=='campaign' and self.campaign.selected:
            self.campaign.selected.algorithm=min(index,self.campaign.unlock)
            self.campaign.selected.motor.controller.reacquire()
        elif self.screen=='academy':self.academy.set_algorithm(index)

    def set_lead(self,value):
        value=max(0,min(2,value))
        if self.screen=='campaign' and self.campaign.selected:
            self.campaign.selected.lead=value
            if self.campaign.selected.algorithm==0:self.campaign.selected.algorithm=1
        elif self.screen=='academy':
            self.academy.set_lead(value)
            if self.academy.step and self.academy.step.scenario=='fixed':self.academy.set_algorithm(1)

    def adjust_lead(self,delta):
        if self.ui.editing():return
        value=self.campaign.selected.lead if self.screen=='campaign' else self.academy.lead
        self.ui.set_slider('lead',max(0,min(2,value+delta)))

    def set_gain(self,index,value):
        if self.screen=='campaign' and self.campaign.selected:
            t=self.campaign.selected;t.gains[index]=value;t.apply_gains()
        elif self.screen=='academy':self.academy.change_gain(index,value)

    def toggle_colour(self):
        if self.screen=='campaign':
            t=self.campaign.selected
            if t:
                if t.colour or t.kind=='sensor':t.sensor_enabled=not t.sensor_enabled
                else:self.campaign.buy_colour()
        else:self.academy.toggle_colour()
        self.save_profile()

    def reward_academy(self):
        # Persist transfer marker with the evidence, making bridge rewards idempotent.
        for record in self.academy.learning.values():
            if record.get('rewarded') and not record.get('campaign_paid'):
                self.campaign.credits+=10;record['campaign_paid']=True
        self.save_profile()

    def answer(self,value):self.academy.answer(value);self.reward_academy();self.ui.signature=None

    def continue_academy(self):self.academy.continue_learning();self.prepare_task();self.save_profile()

    def run_experiment(self):self.academy.run_experiment()

    def show_hint(self):self.academy.runner.feedback=self.academy.step.hint;self.ui.signature=None

    def show_explanation(self):self.academy.runner.feedback=self.academy.step.why;self.ui.signature=None

    def verify_sensor(self):
        g=self.academy;g.upgrades['colour']=1;g.verify_sensor();self.reward_academy()

    def launch_academy_wave(self):self.academy.begin_wave()

    def academy_retry(self):self.academy.retry()

    def recovery(self):
        if self.campaign.running:
            self.notice='Finish this attack before starting a recovery contract.';return
        self.recovery_count+=1
        distance=(180,240,360,480)[self.recovery_count%4]
        speed=(120,240)[self.recovery_count%2]
        target=(40,60,80)[self.recovery_count%3]
        time=distance/speed;lead=time*target
        self.contract={'question':f'A shell covers {distance} units at {speed} units/s. A tank moves at {target} units/s. Choose flight time and lead distance.',
            'answer':f'{time:g} s / {lead:g} units',
            'options':[f'{time:g} s / {lead:g} units',f'{time/2:g} s / {lead/2:g} units',f'{time*2:g} s / {lead*2:g} units'],
            'done':False,'feedback':''}
        # Rotate options to avoid a fixed answer position.
        i=self.recovery_count%3;self.contract['options']=self.contract['options'][i:]+self.contract['options'][:i]
        self.navigate('contract')

    def answer_contract(self,answer):
        task=self.contract
        if not task or task['done']:return
        if answer!=task['answer']:task['feedback']='Try again: time = distance / shell speed, then lead = target speed x time.'
        else:
            task['done']=True;task['feedback']='Contract complete! +20 credits. Your calculation funded fortress reconstruction.'
            self.campaign.credits+=20;self.save_profile();self.audio.play('win',self.prefs)
        self.ui.signature=None

    def zoom_camera(self,factor):
        if self.screen not in ('campaign','academy') or self.ui.pointer_on_ui():return
        self.scene.zoom=max(.7,min(1.5,self.scene.zoom*factor));self.scene.resize()

    def orbit(self,delta):
        if self.screen=='campaign' and not self.ui.editing():
            self.scene.camera_angle=max(-.6,min(.6,self.scene.camera_angle+delta));self.scene.resize()

    def back(self):
        if self.display.pending is not None:self.revert_display();return
        if self.screen=='options':self.close_options()
        elif self.screen=='academy' and self.academy.mode==Scene.CONGRATS:return
        elif self.screen=='campaign' and self.building:self.building=False
        elif self.screen=='title':self.save_profile();self.userExit()
        else:self.navigate('title')

    def on_window(self,window):
        if window!=self.win or not hasattr(self,'ui'):return
        self.ui.resize();self.scene.resize()
        if hasattr(window,'getProperties') and not window.getProperties().getForeground():
            self.campaign.paused=True;self.academy.paused=True

    def sync_scene(self):
        current='academy' if self.screen=='academy' else 'campaign'
        if current!=self.last_scene:self.scene.clear_units();self.last_scene=current
        if self.screen=='academy':
            g=self.academy;trial=g.trial if g.mode==Scene.EXPERIMENT else None
            motor=trial.tower if trial else g.tower
            # Scene adapter keeps the pure academy entity unchanged.
            tower=SimpleNamespace(id=-1,motor=motor,kind='standard',radius=530,solution=trial.solution if trial else g.solution)
            tanks=[trial.tank] if trial else g.tanks
            shells=[trial.projectile] if trial and trial.projectile else g.projectiles
            self.scene.sync([tower],tanks,shells,tower,trial=trial)
        else:
            c=self.campaign
            self.scene.sync(c.towers,c.tanks,c.projectiles,c.selected,build_pad=self.build_pad if self.building else None)

    def frame(self,task):
        dt=ClockObject.getGlobalClock().getDt()
        if self.offscreen:dt=1/60
        if self.display.tick():self.ui.signature=None
        if self.screen=='campaign':
            c=self.campaign;c.update(dt,self.speed)
            if c.finished and not self.campaign_settled:
                self.campaign_settled=True
                if c.success:
                    old=self.records.get(str(c.level))
                    if not old or c.health>old['health']:
                        self.records[str(c.level)]={'health':c.health,'shots':c.shots,'seconds':round(c.time,2)}
                self.save_profile();self.audio.play('win' if c.success else 'hit',self.prefs)
        elif self.screen=='academy':
            before=self.academy.mode;self.academy.update(dt)
            if self.academy.mode!=before:
                self.reward_academy();self.audio.play('win' if self.academy.mode==Scene.CONGRATS else 'hit',self.prefs)
        self.ui.refresh();self.sync_scene()
        return task.cont

    def destroy(self):
        if hasattr(self,'campaign'):self.save_profile()
        super().destroy()
