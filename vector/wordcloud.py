from wordcloud import WordCloud
import matplotlib.pyplot as plt


def generate_wordcloud(df):
    if df.empty:
        return None
    text_dict = dict(zip(df["질문"], df["횟수"]))
    wordcloud = WordCloud(font_path="/System/Library/Fonts/Supplemental/AppleGothic.ttf", background_color="white", width=800, height=400)
    wc = wordcloud.generate_from_frequencies(text_dict)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    return fig