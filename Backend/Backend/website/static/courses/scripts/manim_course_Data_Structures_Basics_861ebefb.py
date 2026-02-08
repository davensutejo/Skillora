
from manim import *
from manim_editor import PresentationSectionType
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

# For code demonstrations if needed
try:
    from manim_code_blocks import Code
except ImportError:
    pass

# For neural network visualization if needed
try:
    from manim_neural_network import NeuralNetworkMobject
except ImportError:
    pass

# For data structure visualization if needed
try:
    from manim_data_structures import Array, LinkedList, Stack, Queue, BinaryTree
except ImportError:
    pass

class DataStructuresBasicsScene(VoiceoverScene):
    def construct(self):
        # Initialize the text-to-speech service
        self.set_speech_service(GTTSService())
        
        # Course title and topic introduction with voice narration
        topic = "Data Structures Basics"
        
        # SECTION 1: Introduction
        self.next_section("Introduction", PresentationSectionType.NORMAL)
        with self.voiceover("Welcome to this educational video on " + topic + "."):
            title = Text(topic, font_size=48)
            self.play(Write(title))
            self.wait(1)
        
        # Subtitle with author information
        with self.voiceover("In this video, we'll explore the key concepts and applications of this important topic."):
            subtitle = Text("An Educational Presentation", font_size=24)
            self.play(title.animate.to_edge(UP), Write(subtitle))
            self.wait(1)
            self.play(FadeOut(subtitle))
        
        # SECTION 2: Overview
        self.next_section("Overview", PresentationSectionType.NORMAL)
        with self.voiceover("Let's start with an overview of what we'll cover today."):
            overview = Text("Overview", font_size=36)
            self.play(ReplacementTransform(title, overview))
            self.wait(1)
            
            # Key topics bullet points
            topics = BulletedList(
                "Core concepts",
                "Key applications",
                "Real-world examples",
                "Practice scenarios",
                font_size=24
            )
            self.play(Write(topics))
            self.wait(2)
            
            # Highlight each topic as we introduce it
            for i in range(len(topics)):
                self.play(topics.animate_item(i, highlight_color=YELLOW), run_time=0.5)
                self.wait(0.5)
            
            self.wait(1)
            self.play(FadeOut(topics), FadeOut(overview))
        
        # SECTION 3: Main Content
        self.next_section("Main Content", PresentationSectionType.NORMAL)
        with self.voiceover("Now, let's dive into the main content of " + topic + "."):
            main_title = Text("Main Content", font_size=36)
            self.play(Write(main_title))
            self.wait(1)
            self.play(FadeOut(main_title))
            
            # Concept 1
            with self.voiceover("First, let's explore the fundamental concepts."):
                concept1 = Text("Key Concept 1", font_size=32)
                self.play(Write(concept1))
                self.wait(1)
                
                # Simple visualization for concept 1
                concept1_viz = Circle(radius=1.5, color=BLUE)
                self.play(ReplacementTransform(concept1, concept1_viz))
                self.wait(1)
                self.play(concept1_viz.animate.set_color(GREEN))
                self.wait(1)
                self.play(FadeOut(concept1_viz))
            
            # Concept 2
            with self.voiceover("Next, let's look at another important aspect."):
                concept2 = Text("Key Concept 2", font_size=32)
                self.play(Write(concept2))
                self.wait(1)
                
                # Simple visualization for concept 2
                concept2_viz = Square(side_length=2, color=RED)
                self.play(ReplacementTransform(concept2, concept2_viz))
                self.wait(1)
                self.play(Rotate(concept2_viz, PI/2))
                self.wait(1)
                self.play(FadeOut(concept2_viz))
        
        # SECTION 4: Application/Example
        self.next_section("Application", PresentationSectionType.NORMAL)
        with self.voiceover("Let's see how these concepts apply in real-world scenarios."):
            application = Text("Practical Application", font_size=36)
            self.play(Write(application))
            self.wait(1)
            self.play(application.animate.to_edge(UP))
            
            # Try to use specialized visualizations based on the topic
            if "programming" in topic.lower() or "coding" in topic.lower() or "algorithm" in topic.lower():
                try:
                    code_str = '''
def example_function(x):
    result = x * 2
    return result

# Call the function
example_function(5)
'''
                    code = Code(
                        code=code_str,
                        tab_width=4,
                        background="window",
                        language="Python",
                        font="Monospace"
                    )
                    self.play(Write(code))
                    self.wait(2)
                    self.play(FadeOut(code))
                except:
                    # Fallback
                    code_viz = Text("Code Example", font_size=24)
                    self.play(Write(code_viz))
                    self.wait(2)
                    self.play(FadeOut(code_viz))
            
            elif "neural network" in topic.lower() or "machine learning" in topic.lower() or "ai" in topic.lower():
                try:
                    nn = NeuralNetworkMobject([3, 4, 2])
                    self.play(Write(nn))
                    self.wait(2)
                    self.play(FadeOut(nn))
                except:
                    # Fallback
                    nn_viz = Text("Neural Network Visualization", font_size=24)
                    self.play(Write(nn_viz))
                    self.wait(2)
                    self.play(FadeOut(nn_viz))
            
            else:
                # Generic visualization
                # Define bounds for LaTeX integration formula
                lower_bound = "a"  # Integration lower bound 
                upper_bound = "b"  # Integration upper bound
                # Construct the LaTeX formula string with explicit values to avoid undefined variable errors
                formula_text = r"f(x) = \int_ + lower_bound + r^ + upper_bound + r g(x) dx"
                formula = MathTex(formula_text)
                self.play(Write(formula))
                self.wait(2)
                self.play(FadeOut(formula))
        
        # SECTION 5: Summary
        self.next_section("Summary", PresentationSectionType.NORMAL)
        with self.voiceover("Let's summarize what we've learned about " + topic + "."):
            conclusion = Text("Summary of key points", font_size=28)
            self.play(Write(conclusion))
            self.wait(2)
            
            # Final title with manim-editor section for easy ending
            self.next_section("Ending", PresentationSectionType.NORMAL)
            with self.voiceover("Thanks for watching this video on " + topic + "."):
                final_title = Text("Thanks for watching!", font_size=36)
                self.play(ReplacementTransform(conclusion, final_title))
                self.wait(2)
    