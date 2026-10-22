import csv
S=['AQUARIUS','ARIES','CANCER','CAPRICORN','GEMINI','LEO','LIBRA','PISCES','SAGITTARIUS','SCORPIO','TAURUS','VIRGO']
pairs=[(a,b) for i,a in enumerate(S) for b in S[i:]]
D=[
("4570110121","Two Aquarians, a hundred big ideas, one shared future.","Which one of you comes up with the wild plans?"),
("4570110641","Aries starts it, Aquarius reinvents it.","Who suggests the next adventure?"),
("4570125580","Cancer brings the home. Aquarius brings the open window.","Which one of you is the homebody?"),
("4570126104","Capricorn builds the plan. Aquarius makes it better.","Who makes the plans in your house?"),
("4570112095","Air meets air, and the conversation never ends.","Who has the last word, Aquarius or Gemini?"),
("4570127160","Opposite signs, one bright orbit.","Who loves the spotlight more?"),
("4570113157","Libra brings the charm, Aquarius brings the spark.","Who picks the restaurant, Libra or Aquarius?"),
("4570113675","One dreams in color, one dreams in ideas.","Which one of you is the daydreamer?"),
("4570128546","Two free spirits who chose the same road.","Where would you two go tomorrow if you could?"),
("4570114301","Scorpio goes deep, Aquarius goes far. Somehow you meet in the middle.","Who keeps the secrets in your house?"),
("4570150148","Taurus keeps it steady, Aquarius keeps it interesting.","Who is the more stubborn one?"),
("4570136319","Virgo perfects the details, Aquarius dreams up the big picture.","Who notices the small things?"),
("4570151370","Two Aries, double the fire, zero boring days.","Who wins the race to the door?"),
("4570151950","Aries leads the way, Cancer makes it feel like home.","Which one of you is the protector?"),
("4570152410","Aries says now, Capricorn says the right way. Together you get there.","Who is more impatient, Aries or Capricorn?"),
("4570152820","Fast feet, quick words, never a dull day.","Who talks the other into the plan?"),
("4570031205","Two fire signs, one warm glow.","Who gets louder at game night?"),
("4570153208","Opposite signs that pull each other closer.","Who decides faster, Aries or Libra?"),
("4570138967","Aries brings the courage, Pisces brings the magic.","Who is the romantic one?"),
("4570154042","Fire and fire, always ready for the next adventure.","Who books the trip first?"),
("4570139913","Fire meets deep water. Nobody said it would be calm.","Aries or Scorpio, who wins the arguments?"),
("4570140539","Aries runs, Taurus takes its time. You still arrive together.","Who is always running late?"),
("4570155846","Aries jumps in, Virgo checks the plan. It works.","Who reads the instructions?"),
("4570141945","Two Cancers, one cozy home, endless care.","Who makes the best comfort food?"),
("4570157258","Cancer holds the heart, Capricorn holds the plan.","Who is the planner in your home?"),
("4570157716","Gemini keeps you laughing, Cancer keeps you close.","Who tells the better stories?"),
("4570143387","A soft Cancer heart meets warm Leo light.","Who is the bigger romantic?"),
("4570143815","Cancer feels everything. Libra keeps the balance.","Which one of you is the Cancer?"),
("4570144239","Two water signs that understand each other without a word.","Who cries first at movies?"),
("4570144663","Sagittarius brings the stories, Cancer brings the home to tell them in.","Who wants to travel more?"),
("4570145103","Two water signs, one deep current.","Who remembers every date?"),
("4570160260","Cancer and Taurus, the coziest pair in the zodiac.","Who is in charge of dinner?"),
("4570160676","Cancer cares, Virgo takes care. A quiet kind of perfect.","Who remembers the little things?"),
("4570161266","Two Capricorns, one big plan, and you will make it happen.","Who writes the lists?"),
("4570147149","Gemini brings the ideas, Capricorn turns them into plans.","Who is the talker and who is the doer?"),
("4570162562","Leo shines, Capricorn builds the stage.","Who takes the lead?"),
("4570163164","Libra brings the grace, Capricorn brings the backbone.","Who makes the final call?"),
("4570148769","Pisces dreams it, Capricorn makes it real.","Which one of you is the dreamer?"),
("4570163968","Sagittarius chases the horizon, Capricorn climbs the mountain.","Mountains or beaches for you two?"),
("4570149603","Quiet strength on both sides, and a loyalty that runs deep.","Who is more loyal, or is it a tie?"),
("4570164962","Two earth signs building something that lasts.","Who is the better saver?"),
("4570165628","Earth meets earth, and everything has its place.","Who keeps the house in order?"),
("4570166282","Two Geminis means four opinions and endless fun.","Who changes plans more often?"),
("4570152121","Gemini brings the wit, Leo brings the warmth.","Who is the life of the party?"),
("4570152561","Two air signs, light and easy, never short of words.","Who keeps the conversation going?"),
("4570153015","Gemini thinks in words, Pisces feels in colors.","Who is the storyteller?"),
("4570153495","Opposite signs who never run out of stories.","Who plans the next trip?"),
("4570154049","Gemini asks the questions, Scorpio knows the answers.","Who is harder to read?"),
("4570169354","Taurus keeps it grounded, Gemini keeps it moving.","Who chooses the movie?"),
("4570155327","Two Mercury signs, both sharp, both curious.","Who wins the word games?"),
("4570155945","Two Leos, one spotlight, and somehow it works.","Who gets the bigger spotlight at home?"),
("4570198669","Leo's fire, Libra's grace, one beautiful match.","Who takes longer to get ready?"),
("4570199091","Leo leads with heart, Pisces follows with soul.","Who is the bigger dreamer?"),
("4570199509","Two fire signs, all warmth and laughter.","Who tells the best jokes?"),
("4570214304","Leo shines bright, Scorpio burns deep.","Who is the more intense one?"),
("4570214784","Leo loves the spotlight, Taurus loves the comfort. You make room for both.","Who is more stubborn?"),
("4570200893","Leo brings the big gestures, Virgo the thoughtful details.","Who plans the surprises?"),
("4570201313","Two Libras, a perfectly balanced pair.","Who takes longer to decide?"),
("4570216030","Libra loves beauty, Pisces lives in it.","Who is the hopeless romantic?"),
("4570202333","Libra brings the charm, Sagittarius brings the adventure.","Who says yes to every plan?"),
("4570202793","Libra keeps it light, Scorpio keeps it real.","Who wins the staring contest?"),
("4570203229","Two Venus signs who love the finer things.","Who has the better taste?"),
("4570203731","Virgo brings the care, Libra brings the harmony.","Who keeps the peace at home?"),
("4570204167","Two Pisces, one shared dream.","Who is the dreamier one?"),
("4570204681","Sagittarius explores the world, Pisces explores the heart.","Who is the wanderer?"),
("4570205473","Water and water, deep and devoted.","Who feels it more?"),
("4570205899","Taurus holds steady, Pisces brings the dreams.","Who is the calm one?"),
("4570220634","Virgo grounds, Pisces inspires. Opposites in the best way.","Who keeps the two of you organized?"),
("4570206865","Two Sagittarians, one passport stamp at a time.","Where is your next trip?"),
("4570221662","Sagittarius brings the freedom, Scorpio brings the depth.","Who is the bigger mystery?"),
("4570207855","Taurus loves home, Sagittarius loves the road. Love finds the way.","Stay in or go out tonight?"),
("4570208321","Sagittarius says let's go, Virgo already packed.","Who is the planner on trips?"),
("4570209015","Two Scorpios, one intense and loyal bond.","Who keeps the bigger secrets?"),
("4570224058","Opposite signs with the same loyal heart.","Who gives in first?"),
("4570210411","Virgo notices everything, Scorpio feels everything.","Who reads the other better?"),
("4570225672","Two Taurus hearts, one cozy life.","Who guards the snacks?"),
("4570226386","Two earth signs building a calm, beautiful life.","Who is the homebody?"),
("4570227104","Two Virgos, every detail in its place.","Who folds the laundry better?"),
]
assert len(D)==78==len(pairs)
V=[("A printed keepsake for anniversaries, weddings, or just because.","#anniversarygift"),
   ("A printed keepsake made for the two of you.","#astrologyart"),
   ("A printed gift for an engagement, a wedding, or a first home together.","#weddinggift")]
with open('AstroLove_IG_FB_Captions_78_20261001.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['pair','listing_id_DOGRULANMADI','ig_caption','fb_caption','fb_first_comment'])
    for i,((a,b),(lid,hook,q)) in enumerate(zip(pairs,D)):
        A,B=a.title(),b.title(); tag='#'+(a+b).lower()
        made="Your shared sign becomes one original symbol, with both your names and a short line of your own." if a==b else "We merged both signs into one original symbol, then added your names under each sign and a short line of your own."
        l4,rot=V[i%3]
        base=[f"{A} & {B} personalized zodiac couple print.",hook,made,l4,q]
        ig="\n".join(base+["Link in bio: AstroLoveArt on Etsy",f"{tag} #zodiaccouple #couplegift #personalizedgift {rot}"])
        fb="\n".join(base+["Shop link in the first comment.",f"{tag} #zodiaccouple #couplegift"])
        for t in (ig,fb): assert '—' not in t and '–' not in t
        w.writerow([f"{a}_{b}",lid,ig,fb,f"Find {A} & {B} in our Etsy shop: https://www.etsy.com/listing/{lid}"])
print('ok')
