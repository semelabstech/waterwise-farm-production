import os
from fpdf import FPDF
from datetime import datetime

class PremiumDoc(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load Unicode font to support accents
        font_path = r"C:\Windows\Fonts\arial.ttf"
        font_bold_path = r"C:\Windows\Fonts\arialbd.ttf"
        font_italic_path = r"C:\Windows\Fonts\ariali.ttf"
        if os.path.exists(font_path):
            self.add_font("Arial", "", font_path)
            self.add_font("Arial", "B", font_bold_path)
            self.add_font("Arial", "I", font_italic_path)
            self.main_font = "Arial"
        else:
            self.main_font = "helvetica"

    def header(self):
        if self.page_no() > 1:
            self.set_font(self.main_font, 'I', 8)
            self.set_text_color(120)
            self.cell(0, 10, "Documentation Système d'Irrigation de Précision — IA & Télédétection", 0, 0, 'R')
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.main_font, 'I', 8)
        self.set_text_color(120)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font(self.main_font, 'B', 18)
        self.set_text_color(27, 94, 32) # Deep Green
        self.cell(0, 15, title, 0, 1, 'L')
        self.set_draw_color(76, 175, 80)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(5)

    def section_title(self, title):
        self.set_font(self.main_font, 'B', 13)
        self.set_text_color(56, 142, 60) # Green
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

    def body_text(self, text):
        self.set_font(self.main_font, '', 11)
        self.set_text_color(50)
        self.multi_cell(0, 6, text)
        self.ln(4)

    def image_with_caption(self, path, caption, w=170):
        if os.path.exists(path):
            # Centering
            x = (210 - w) / 2
            self.image(path, x=x, y=self.get_y(), w=w)
            self.ln( (w/170) * 100 ) # Adjust vertical space based on width (approx for 16:9)
            self.set_font(self.main_font, 'I', 9)
            self.set_text_color(100)
            self.cell(0, 10, caption, 0, 1, 'C')
            self.ln(2)

def generate_premium_doc():
    pdf = PremiumDoc()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Paths to assets
    logo_path = r"C:\Users\G1325\.gemini\antigravity\brain\25b08745-63a4-4cf1-96b3-2f998cf02bb7\precision_agri_logo_1776735917666.png"
    arch_path = r"C:\Users\G1325\.gemini\antigravity\brain\25b08745-63a4-4cf1-96b3-2f998cf02bb7\phd_architecture_diagram_1776735940122.png"
    
    # Screenshots
    ss_home = r"C:\Users\G1325\.gemini\antigravity\brain\25b08745-63a4-4cf1-96b3-2f998cf02bb7\home_page_1776755883669.png"
    ss_map = r"C:\Users\G1325\.gemini\antigravity\brain\25b08745-63a4-4cf1-96b3-2f998cf02bb7\map_page_1776756005631.png"
    ss_stress = r"C:\Users\G1325\.gemini\antigravity\brain\25b08745-63a4-4cf1-96b3-2f998cf02bb7\stress_page_1776756023813.png"
    ss_forecast = r"C:\Users\G1325\.gemini\antigravity\brain\25b08745-63a4-4cf1-96b3-2f998cf02bb7\forecast_page_1776756049547.png"
    ss_recommendations = r"C:\Users\G1325\.gemini\antigravity\brain\25b08745-63a4-4cf1-96b3-2f998cf02bb7\recommendations_page_1776756076797.png"
    ss_report = r"C:\Users\G1325\.gemini\antigravity\brain\25b08745-63a4-4cf1-96b3-2f998cf02bb7\report_page_1776756117452.png"

    # --- COVER PAGE ---
    pdf.add_page()
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=80, y=40, w=50)
    
    pdf.set_y(100)
    pdf.set_font(pdf.main_font, 'B', 28)
    pdf.set_text_color(27, 94, 32)
    pdf.multi_cell(0, 15, "SYSTÈME D'IRRIGATION DE PRÉCISION PAR INTELLIGENCE ARTIFICIELLE", 0, 'C')
    
    pdf.ln(10)
    pdf.set_font(pdf.main_font, 'B', 16)
    pdf.set_text_color(76, 175, 80)
    pdf.cell(0, 10, "Documentation Technique & Showcase Produit", 0, 1, 'C')
    
    pdf.ln(40)
    pdf.set_font(pdf.main_font, '', 12)
    pdf.set_text_color(100)
    pdf.multi_cell(0, 7, "Une plateforme intégrée combinant Télédétection (Sentinel-2), Météo (Informer Transformer) et IoT pour une gestion durable des ressources hydriques au Maroc.", 0, 'C')
    
    pdf.set_y(250)
    pdf.set_font(pdf.main_font, 'B', 11)
    pdf.set_text_color(0)
    pdf.cell(0, 10, "ÉDITION SIAM 2026 — RAPPORT FINAL", 0, 1, 'C')
    
    # --- INTRODUCTION ---
    pdf.add_page()
    pdf.chapter_title("1. VISION ET OBJECTIFS")
    pdf.body_text("Le Maroc traverse un stress hydrique critique. Notre solution propose de transformer l'irrigation traditionnelle en un système piloté par la donnée. En utilisant l'imagerie multispectrale, nous pouvons voir ce que l'œil humain ne perçoit pas : le stress hydrique précoce au cœur des feuilles.")
    
    pdf.section_title("Architecture Globale")
    if os.path.exists(arch_path):
        pdf.image(arch_path, x=20, y=pdf.get_y(), w=170)
        pdf.ln(95)
    
    # --- SHOWCASE INTERFACE ---
    pdf.add_page()
    pdf.chapter_title("2. INTERFACE ET EXPÉRIENCE UTILISATEUR")
    
    pdf.section_title("2.1 Tableau de Bord Principal (Command Center)")
    pdf.body_text("La page d'accueil regroupe les indicateurs clés de performance (KPIs) : économies d'eau, distribution du stress et alertes météo en temps réel.")
    pdf.image_with_caption(ss_home, "Figure 1: Interface de contrôle centralisée avec KPIs dynamiques")
    
    pdf.add_page()
    pdf.section_title("2.2 Cartographie Géospatiale")
    pdf.body_text("L'intégration de Leaflet permet de visualiser les parcelles avec un code couleur simple (Vert, Jaune, Orange, Rouge) basé sur le NDVI et les capteurs IoT.")
    pdf.image_with_caption(ss_map, "Figure 2: Carte interactive montrant les zones de stress par région")
    
    pdf.add_page()
    pdf.section_title("2.3 Analyse IA du Stress Hydrique")
    pdf.body_text("Le modèle U-Net segmente les images Sentinel-2 pour identifier les zones critiques. Chaque patch de 256x256 pixels est analysé pour extraire la teneur en eau (NDMI).")
    pdf.image_with_caption(ss_stress, "Figure 3: Analyse granulaire du stress hydrique via vision par ordinateur")
    
    pdf.add_page()
    pdf.section_title("2.4 Prévisions Temporelles (ET0)")
    pdf.body_text("L'Informer Transformer prédit l'évapotranspiration à 48h, permettant d'anticiper les besoins d'irrigation avant même que les plantes ne souffrent.")
    pdf.image_with_caption(ss_forecast, "Figure 4: Courbes de prévisions météorologiques et d'évapotranspiration")
    
    pdf.add_page()
    pdf.section_title("2.5 Recommandations et Planning")
    pdf.body_text("Le moteur de fusion calcule le volume précis (en mm) pour chaque zone, générant un planning horaire optimisé pour minimiser l'évaporation.")
    pdf.image_with_caption(ss_recommendations, "Figure 5: Plan d'irrigation ciblée et calcul de budget hydrique")
    
    pdf.add_page()
    pdf.section_title("2.6 Rapport de Performance")
    pdf.body_text("Un résumé complet des économies réalisées (ici 36.8%) et du bilan hydrique de l'exploitation.")
    pdf.image_with_caption(ss_report, "Figure 6: Rapport final d'exploitation et métriques d'économie d'eau")

    # --- TECHNICAL DETAILS ---
    pdf.add_page()
    pdf.chapter_title("3. FONDATIONS TECHNIQUES")
    
    pdf.section_title("3.1 Le Moteur IA (U-Net & Informer)")
    pdf.body_text("- U-Net Attention : Encodeur/Décodeur avec portes d'attention pour filtrer le bruit spectral.\n- Informer Transformer : Mécanisme de ProbSparse Attention pour une prévision à long terme efficace.")
    
    pdf.section_title("3.2 Fusion de Données")
    pdf.body_text("Equation de Fusion : Score = 0.40 * Satellite + 0.35 * Météo + 0.25 * IoT.\nLe système normalise les indices NDVI/NDMI, l'ET0 calculé via Penman-Monteith et les relevés d'humidité du sol pour une décision robuste.")

    # --- SAVE ---
    output_path = r"c:\Users\G1325\Downloads\Theme Agriculture & Stress Hydrique\DOCUMENTATION_PREMIUM_AGRICULTURE_IA.pdf"
    pdf.output(output_path)
    print(f"Documentation Premium générée : {output_path}")

if __name__ == "__main__":
    generate_premium_doc()
