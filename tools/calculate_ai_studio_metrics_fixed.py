#!/usr/bin/env python3
"""
Calculate CER/WER for AI Studio transcriptions of the 6 blocked files
CORRECTED MAPPINGS based on ground truth headlines
"""

import re
from pathlib import Path

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate Character Error Rate."""
    ref_norm = normalize_text(reference)
    hyp_norm = normalize_text(hypothesis)
    if len(ref_norm) == 0:
        return 0.0 if len(hyp_norm) == 0 else 1.0
    distance = levenshtein_distance(ref_norm, hyp_norm)
    cer = distance / len(ref_norm)
    return cer

def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate."""
    ref_words = normalize_text(reference).split()
    hyp_words = normalize_text(hypothesis).split()
    if len(ref_words) == 0:
        return 0.0 if len(hyp_words) == 0 else 1.0
    distance = levenshtein_distance(' '.join(ref_words), ' '.join(hyp_words))
    wer = distance / len(' '.join(ref_words))
    return wer

# CORRECTED File mappings based on ground truth headlines
files = {
    '3200810451': """EXTRAORDINARY DEATH OF A POLICE CONSTABLE.

MR. JOHN TROUTBECK, the coroner for Westminster, held an inquiry into the circumstances attending the death of Police-constable Joseph Daniels, 259 E, aged twenty-seven years, who was killed early on Sunday morning while taking a prisoner to Bow-street Police-station. Superintendent Steggles, of the E division, was present. Joseph Daniels, a registration agent, of 9, Meeting-House-lane, Peckham, identified the deceased as his son, lately residing at Jubilee-buildings, Waterloo-road. Some time ago he had erysipelas in the face, and the divisional surgeon ordered him to have some of his teeth extracted and replaced by false ones. These he was wearing at the time of his death. Police-constable Alfred Smith, 379 E, said that on Sunday morning at about 12.20 he was in Kemble-street, Clare-market, taking a prisoner to Bow-street Police-station. A crowd of several hundred persons had assembled, and an attempt to rescue the man was made. Witness blew his whistle, and in response the deceased came running up. He took hold of the prisoner's other arm, and they had only proceeded a few yards, when witness missed the deceased, and on looking round saw him lying on the pavement. Another constable came up, and witness went on his way. Police-constable William Stewart, 350 E, said that he was on duty in Newcastle-street, when he heard the whistle blow, and on going to Kemble-street, saw the two constables with a man in custody. Witness broke through the crowd, and then saw the deceased lying on the ground. He immediately undid his collar and sent for an ambulance, on which he conveyed the unfortunate man to the hospital. By the Coroner: The deceased was not knocked down, kicked, or otherwise assaulted. Dr. Eric Law Pritchard, house physician at King's College Hospital, said that deceased was dead when admitted. He had made a post-mortem examination, which revealed that the deceased was an exceedingly healthy man. Just about the larynx witness found a set of false teeth impacted, which had produced suffocation, the cause of death. The teeth were of very inferior make; no doubt they became loosened through the deceased running, and an inspiration drew them down his throat. The jury returned a verdict of accidental death, and added that they thought deceased was over anxious to do his duty.""",

    '3200810720': """MYSTERIOUS DEATH OF A CHILD.

THE inquest on the body of the child Anne Concannon, whose body, which had been stripped of boots and earrings, was found in a closet on the 2nd inst., was concluded on Wednesday. The evidence given did not throw any light on the child's death, but one witness, who had seen the child during the day, prevaricated and contradicted herself so much as to call forth remonstrances from the jury and a warning from the coroner. Medical evidence was to the effect that death was due to suffocation, and that the child bore evidence of having been assaulted. The jury, after being absent nearly an hour, found "That the deceased had died from slow suffocation, but that there was not sufficient evidence to show how the child had got into the position in which it was found."

A SOUTHAMPTON correspondent states that during the Queen's residence at Osborne an unpleasant incident occurred. Her Majesty, as everybody knows, drives through Cows with the greatest freedom, and the presence of Mr. Sweeney, the police officer in attendance at Osborne, has been scarcely more than a formality. But a few days ago, as the Queen was driving back to Osborne, a gentlemanly-looking person inquired of a bystander whether that was the Queen who was approaching. On being told that it was, he rapidly advanced to the carriage, and in a very violent manner said he was a foreign count, and that he and many others had sworn that if the Queen did not resign they would kill her. The attendants at once removed the man, who was found to be demented. Her Majesty showed great presence of mind. A day or two later a telegram was received at Osborne stating that "69" would do himself the pleasure of calling upon the Queen. In due course a man arrived, who said he had occupied No. 69 bed in a hospital visited some years ago by her Majesty, and that he had called upon the Queen to say that he had no money, and would be glad if she would assist him. In this case also it proved that the man was demented. Only 9d. was found upon him, and he appeared to have been in good circumstances at some time.

A VIOLENT SEAMAN.—Robert William Kermur, twenty-seven, a seaman, of 2, Prince of Wales-road, Custom-house, was charged, at the West Ham Police-court, before Mr. Baggallay, with being disorderly, and with assaulting Constable Bland, 393 K, in Francis-street, Canning-town, on the 17th inst. At about half-past eight on Wednesday night the constable was called to Francis-street, where he found the prisoner acting like a madman, and he had, was stated, knocked a woman down, and also kicked a child. When arrested he became very violent, and kicked the officer in the stomach. Ten days.""",

    '3200810876': """A PUTNEY MYSTERY.

MR. HICKS, coroner, held an inquiry at Putney into the circumstances attending the death of Frederick Robbins, aged forty-eight years, an artist, lately residing at Richmond-road, Putney, whose mutilated remains wero found on the South-Western Railway at Putney Station on Sunday. Edwin Nixey, a brewer, of Brunswick House, Hartlepool, identified the deceased as his brother-in-law, whom he last saw alive three weeks ago, when he was in excellent health. He was a married man, and to witness's knowledge he was not in monetary troubles.— William Warren, a chemist, of Richmond-road, stated that the deceased resided with him. He suffered greatly from deafness, was rather short-sighted, and wore spectacles. In consequence of the wet weather the deceased remained at home on Sunday, but at seven o'clock went out, saying he was going for a stroll. As he did not return at eleven o'clock inquiries were made, and it was found that the deceased had been discovered on the line." He was in no monetary difficulties, and a most unlikely man to commit suicide. James William Burrowes, porter at Putney Station, stated that after the five minutes past ten p.m. milk train had left the station, he observed the deceased lying in the four-foot-way. His hat and umbrella were lying close by. A doctor pronounced life extinct. William Lawrence, guard of the up Kingston train, said he examined the carriages, and found all the doors were properly closed on both sides. By the Jury: He noticed a slight jerk of the train, but thought it was only caused by an umbrella or stick on the line. Dr. William J. Sheppard said the deceased, on examination of the body, revealed that both shoulders were crushed, the arms nearly amputated, and the chest crushed in. Death was instantaneous. The jury returned an open verdict.""",

    '3206201407': """CHILD MURDER AND MUTILATION.

On Tuesday, considerable excitement prevailed in Peckham and its vicinity from the discovery of the body of a female child in the house of Mr. Whitby, a highly respectable inhabitant of James street, Commercial-road, Peckham, which had undergone the most extraordinary mutilation by the inhuman mother.
It appears that on or about the 16th instant, a young woman, named Mercy Steer, servant to Mr. Whitby, seemed to be in very ill-health, and her mistress conceived that all was not right. She, however, left her service on the 20th inst, without any elucidation taking place, and proceeded to her native village, a place called Billinghurst, near Petworth, in the county of Sussex. Having there continued in an ill state of health she found it necessary to obtain medical advice, and the result of which was, that she was found to have been recently delivered of a child. Giving no satisfactory account of this, the circumstance was communicated to Mr. Hay, one of the churchwardens of Billinghurst, who, having ascertained that Mary Steer had been in service at Peckham, a communication was at once forwarded to Mr. Superintendent Lund, of the P division, who placed the matter in the hands of the police, who proceeded to the house of Mr. Whitby, for the purpose of making an examination. On searching the chamber which had been occupied by the woman Steer, there at first appeared no indications of any child birth having recently taken place. A closer inspection, however, showed that the sheets, blankets, and bedding, had been recently washed, with a view to remove any stains, but on the pillows there were some visible traces of blood. A further search showed some marks on the boards of the floor, to obliterate which, some evident, though ineffectual, attempts had been made. A closer investigation brought to light a piece of bedside carpeting, saturated with unequivocal marks of a recent child-birth.
This discovery led to a more searching examination, and after removing the pan of the water-closet, the right hand of an infant was discovered on the top of the soil. Proceeding further in the examination, the various fragments of the body of a newly-born female child were brought forth, but which had been separated into so many minute portions, as to be almost calculated to destroy all traces of the previous existence of any human body. The object of this mutilation, it would seem, was to force the respective portions through the soil pipe, for which purpose the skull had been divided longitudinally, and the vertebræ had undergone a similar process. The hands had been amputated at the wrists, and the feet at the ankles, the arms at the elbows, the thighs at the hips, and the abdomen divided into several particles. As a matter of course, the heart, spleen, and other portions of the intestines were also subdivided. From a cursory view it would appear that the child was born alive, and must therefore have been subjected to horrid mutilation by the inhuman mother.
The woman Mercy Steer is now under the surveillance of the Sussex constabulary, and when sufficiently restored to health will be brought to London, in order to undergo the necessary judicial inquiry.""",

    '3206270938': """THREE MURDER TRIALS.
At the Court of Session, at Glasgow, on Friday, Thos. White, indicted for the murder of John Dawson by fatally stabbing him, was found "Guilty" of manslaughter and sentenced to 10 years' penal servitude; James Glen, charged with the murder of his wife, was found to be insane and ordered to be detained during her Majesty's pleasure; and Jessie McCallum, tried for the murder of her infant child, was convicted of manslaughter, and sentenced to penal servitude for six years.

A SHOCKING CONDITION OF THINGS.—
Mr. Baxter held an inquest at the Poplar town-hall on Friday respecting the death of Edward McCarthy, aged five months, the son of a labourer, residing at 37, Woolmore-street, Poplar. Margaret McCarthy, the mother, made a rambling statement, and kept moaning and groaning, but all that could be gathered from her evidence was that she went to bed about two a.m. on Christmas day, and when she awoke about seven she found the child dead. Catherine Shean, sister of the last witness, stated she visited Mrs. McCarthy on Christmas eve, and stayed till two in the morning. She noticed that the child appeared ill, and in company with the mother they took it to Dr. Harvey's, but could make no one hear. They had nothing to drink, and when she left they were all sober. The Coroner: Is the mother sober now? Witness: Yes. The Coroner (with surprise): Oh. I only wanted to know what your idea of soberness was. Dr. Thomas Harvey stated that the cause of death was suffocation by overlaying. There had been someone in his surgery the whole day, so that anyone who had gone there would have been attended to. The jury returned a verdict of "Accidental death," the foreman suggesting that the mother should be censured, but the coroner said that it would be useless doing so, as she would forget all about it when she was sober.

MANBY'S PETROLITE SOAP POWDER saves hours of needless rubbing and scrubbing, and is most comforting to the hands. Beats everything for washing linen, flannels, house cleaning, &c. Sold in penny packets, and cases containing 4lb packets, 3s.—Works, Augustus-street, N.W.—[ADVT]""",

    '3206313966': """SUICIDE OF A PORTR PAINTER.

Mr. Brent has just held an inquiry at the George, Brook-street, Holborn, touching the death of Mr. Geo. Smart, a well-known portrait painter, aged forty-six, who committed self-destruction, under very painful circumstances, in a miserable lodging, in Bell-court, Gray's-inn-lane. The deceased was in very reduced circumstances, and had lived in his late lodging nearly three years, during which period he never permitted any person to enter his apartment, no doubt induced from a mistaken feeling of shame at its mean appearance. His own aspect at all times was exceedingly wretched, and his tattered clothes frequently attracted the commiseration of the neighbours, for it was well known who he was, and his talents were appreciated by those about him, to whom he was in the habit of exhibiting some of the portraits which he painted. A short time before his unhappy death he spoke to his landlord about being unable to pay his rent, some two or three shillings a week, when the landlord, much to his credit, instead of upbraiding the poor fellow and giving him notice to leave, told him that he might run on as long as he pleased without paying, in the hope that the times would get better with him. Mr. Smart was last seen alive on Saturday, and his non-appearance from that period up to Wednesday afternoon excited the apprehension of his landlord; the more so, as everything appeared so quiet in the room. Obtaining no answer to repeated knockings at his door, the landlord at length, with the assistance of the police, forcibly entered the apartment, when a terrible spectacle met their view, as the poor creature's remains, in a fearfully putrefied state, lay stretched on some dirty old rags, which had served for his bed, and there was a deep gash across his throat, which, to use the words of Mr. Strange, the surgeon, who was called to see the body, "nearly divided his head from the trunk, the wound extending down to the very vertebrae." The razor with which the dead had been committed was lying near him. In the room were found a stale loaf, fourpence-halfpenny in money, and some ragged garments, which had served the deceased for clothing by day and for a bed at night. The only article of furniture was a chair without a bottom. There were likewise found in the room two beautifully executed portraits by the deceased, of a lady and gentleman; the former not quite finished. The deceased had been very eccentric in his habits, and had taken to intemperance. At the suggestion of the coroner, the jury returned a verdict of suicide, leaving the state of the deceased's mind an open verdict."""
}

gt_dir = Path("/home/jic823/ocr_bldata/25439023/BLN600/Ground Truth")

print("AI Studio Transcription Quality Assessment")
print("="*70)
print()

total_cer = 0
total_wer = 0
count = 0

for file_id, ocr_text in files.items():
    gt_file = gt_dir / f"{file_id}.txt"
    if not gt_file.exists():
        print(f"{file_id}: Ground truth not found")
        continue
    with open(gt_file, 'r', encoding='utf-8', errors='replace') as f:
        gt_text = f.read()
    cer = calculate_cer(gt_text, ocr_text)
    wer = calculate_wer(gt_text, ocr_text)
    total_cer += cer
    total_wer += wer
    count += 1
    print(f"{file_id}:")
    print(f"  CER: {cer*100:.2f}%")
    print(f"  WER: {wer*100:.2f}%")
    print(f"  GT length: {len(gt_text)} chars")
    print(f"  OCR length: {len(ocr_text)} chars")
    print()

if count > 0:
    avg_cer = (total_cer / count) * 100
    avg_wer = (total_wer / count) * 100
    print("="*70)
    print(f"Average CER: {avg_cer:.2f}%")
    print(f"Average WER: {avg_wer:.2f}%")
    print(f"Files processed: {count}")
    print("="*70)
