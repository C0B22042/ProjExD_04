import math
import random
import sys
import time

import pygame as pg
from pygame.sprite import AbstractGroup


WIDTH = 1600  # ゲームウィンドウの幅
HEIGHT = 900  # ゲームウィンドウの高さ


def check_bound(obj: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内か画面外かを判定し，真理値タプルを返す
    引数 obj：オブジェクト（爆弾，こうかとん，ビーム）SurfaceのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj.left < 0 or WIDTH < obj.right:  # 横方向のはみ出し判定
        yoko = False
    if obj.top < 0 or HEIGHT < obj.bottom:  # 縦方向のはみ出し判定
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"ex04/fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.muteki_img = pg.transform.laplacian(self.image)
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = -1


    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"ex04/fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def change_state(self, state, hyper_life):
        """
        こうかとんの肉体強化モード
        引数1 状態
        引数2 発動時間
        """
        self.state = state
        self.hyper_life = hyper_life


    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                self.rect.move_ip(+self.speed*mv[0], +self.speed*mv[1])
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        if check_bound(self.rect) != (True, True):
            for k, mv in __class__.delta.items():
                if key_lst[k]:
                    self.rect.move_ip(-self.speed*mv[0], -self.speed*mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
            self.muteki_img = pg.transform.laplacian(self.image)
        if self.state == "hyper":
            self.hyper_life -= 1
            screen.blit(self.muteki_img, self.rect)
        else:
            screen.blit(self.image, self.rect)
    
    def get_direction(self) -> tuple[int, int]:
        return self.dire
    

class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        self.rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        self.image = pg.Surface((2*self.rad, 2*self.rad))
        pg.draw.circle(self.image, color, (self.rad, self.rad), self.rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height/2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(+self.speed*self.vx, +self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load(f"ex04/fig/beam.png"), angle, 2.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(+self.speed*self.vx, +self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class NeoBeam:#課題４
    def  __init__(self, bird: Bird, num: int):#num=ビームの個数(1~14)
        self.beam_num = num
        self.bird = bird
        self.vx, self.vy = bird.get_direction()#定義105　鳥の動きの向き。
        self.angle = math.degrees(math.atan2(-self.vy, self.vx))#vx, vyから度数(360度)を求める

    def gen_beams(self):
        self.beam_list = []
        i = 0
        for num in (0, -25, 25, -50, 50, -75, 75, -100, 100, -125, 125, -150, 150, -175):
            self.beam_list.append(Beam(self.bird, self.angle+num))
            i += 1
            if i >= self.beam_num:
                break
        return self.beam_list

class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load("ex04/fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()

class Shield(pg.sprite.Sprite):
    """
    CapsLockキーを押下した際に
    こうかとんの前に防御壁を出現させるクラス
    """

    def __init__(self, bird: Bird, life: int = 400):
        """
        防御壁surface作成
        引数１：bird...こうかとん
        引数２：life...発動時間
        """
        super().__init__()

        self.vx, self.vy = bird.get_direction()
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.Surface((20, bird.rect.height*2)), angle, 1.0)

        pg.draw.rect(self.image, (0, 0, 0), pg.Rect(0, 0, 20, bird.rect.height*2))
        self.rect = self.image.get_rect()
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.life = life


    def update(self):
        """
        lifeに応じて防御壁を削除
        """
        self.life -= 1
        if self.life < 0:
            self.kill()



class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"ex04/fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vy = +6
        self.bound = random.randint(50, HEIGHT/2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        self.rad = max([self.rect[i+2] for i in range(2)])//2

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.centery += self.vy


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.score = 0
        self.image = self.font.render(f"Score: {self.score}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def score_up(self, add):
        self.score += add

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.score}", 0, self.color)
        screen.blit(self.image, self.rect)

class GravitySphere(pg.sprite.Sprite):
    """
        重力球に関するclass
    """
    def __init__(self, bird: Bird, effect_time: int = 500, sphere_radius: int = 200) -> None:
        """
            変数初期化
        :param effect_time: 効果時間-Default:500
        """
        super().__init__()

        # variables
        self.effect_time = -effect_time
        self.rad = sphere_radius

        # surface
        self.image = pg.Surface([sphere_radius*2 for i in range(2)])
        pg.draw.rect(self.image, [255, 255, 255], [0, 0]+[sphere_radius*2 for i in range(2)])
        self.image.set_colorkey([255, 255, 255])
        pg.draw.circle(self.image, [0, 0, 0], [sphere_radius for i in range(2)], sphere_radius)
        self.image.set_alpha(191)
        self.rect = self.image.get_rect()
        self.rect.center = bird.rect.center

    def update(self, bird: Bird) -> None:
        """
            更新
        """
        if self.effect_time >= 0:
            self.kill()
            return
        self.rect.center = bird.rect.center
        self.effect_time += 1
        return 

class NeoGravity(pg.sprite.Sprite):
    """
        超重力砲（超協力重力場）に関するclass
    """
    def __init__(self, effect_time: int = 400):
        """
            変数初期化
        :param effect_time: 効果時間-Default:400
        self.__effect_time = -effect_time
        """
        super().__init__()

        # surface
        self.__effect_time = -effect_time
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(127)
        self.rect = self.image.get_rect()

    def update(self) -> None:
        """
            更新
        :return: None
        """
        if self.__effect_time >= 0:
            self.kill()
        self.__effect_time += 1
        return

def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load("ex04/fig/pg_bg.jpg")
    score = Score()
    beam_many = 2

    bird = Bird(3, (900, 400))

    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    neo_gravitys = pg.sprite.Group()
    gravity_spheres = pg.sprite.Group()
    shields = pg.sprite.Group()
    bird.change_state("normal", -1)

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0

            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT and score.score >= 100:
                score.score -= 100
                bird.change_state("hyper", 500)

            if event.type == pg.KEYDOWN and event.key == pg.K_CAPSLOCK and len(shields) == 0 and score.score >= 50:
                shields.add(Shield(bird))
                score.score -= 50

            if event.type == pg.KEYDOWN and event.key == pg.K_TAB and score.score >= 50:
                gravity_spheres.add(GravitySphere(bird))
                score.score -= 50
        
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN and score.score >= 200:
                neo_gravitys.add(NeoGravity())
                score.score -= 200
                
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if key_lst[pg.K_LSHIFT]:#ビーム複数打つ
                    beam = NeoBeam(bird, beam_many)#(1~14)
                    beams.add(beam.gen_beams())
                
                else:#ビーム１つ打つ
                    beam = NeoBeam(bird, 1)
                    beams.add(beam.gen_beams())

            if event.type == pg.KEYDOWN and event.key == pg.K_a and score.score >= beam_many*10 and beam_many < 14:
                score.score_up(-beam_many*10)
                beam_many += 1
           
            if event.type == pg.KEYDOWN and event.key == pg.K_LSHIFT:
                bird.speed = 20
            if event.type == pg.KEYUP and event.key == pg.K_LSHIFT:
                bird.speed = 10
        
        if bird.hyper_life < 0:
            bird.change_state("normal", -1)
        
        if len(neo_gravitys) == 0:
            screen.blit(bg_img, [0, 0])
        else:
            screen.blit(bg_img, [random.randint(-1,1) for i in range(2)])

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.score_up(1000)  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.score_up(1)  # 1点アップ
        
        # neo gravity collide
        for emy in pg.sprite.groupcollide(emys, neo_gravitys, True, False).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.score_up(10)  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト
        for bomb in pg.sprite.groupcollide(bombs, neo_gravitys, True, False).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.score_up(1)  # 1点アップ

        for gravity_sphere in gravity_spheres:
            gra_sph_center = list(gravity_sphere.rect.center)
            for emy in emys:
                difference = [list(emy.rect.center)[i] - gra_sph_center[i] for i in range(2)]
                direct_distance = math.sqrt(math.pow(difference[0], 2) + math.pow(difference[1], 2))
                if direct_distance < gravity_sphere.rad + emy.rad:
                    exps.add(Explosion(emy, 100))  # 爆発エフェクト
                    score.score_up(10)  # 10点アップ
                    bird.change_img(6, screen)  # こうかとん喜びエフェクト
                    emy.kill()
            for bomb in bombs:
                difference = [list(bomb.rect.center)[i] - gra_sph_center[i] for i in range(2)]
                direct_distance = math.sqrt(math.pow(difference[0], 2) + math.pow(difference[1], 2))
                if direct_distance < gravity_sphere.rad + bomb.rad:
                    exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                    score.score_up(1)  # 1点アップ
                    bomb.kill()
          
        for emy in pg.sprite.groupcollide(emys, shields, True, False).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.score_up(10)  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.score_up(1)  # 1点アップ
            
        if bird.state == "hyper":
            for bomb in pg.sprite.spritecollide(bird, bombs, True):
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.score_up(1)  # 1点アップ

        if len(pg.sprite.spritecollide(bird, bombs, True)) != 0:
            bird.change_img(8, screen) # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        neo_gravitys.update()
        neo_gravitys.draw(screen)
        gravity_spheres.update(bird)
        gravity_spheres.draw(screen)
        score.update(screen)
        shields.update()
        shields.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
