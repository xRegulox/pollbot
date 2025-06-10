import io
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# Use Agg backend to prevent issues with missing display
matplotlib.use('Agg')

def generate_results_chart(title, labels, values, chart_type='bar'):
    """
    Generate a chart for poll results
    
    Parameters:
    - title: Chart title
    - labels: List of option labels
    - values: List of vote counts
    - chart_type: Type of chart ('bar' or 'pie')
    
    Returns:
    - BytesIO object containing the chart image
    """
    plt.figure(figsize=(10, 6))
    
    # Use Discord-style colors
    colors = ['#5865F2', '#57F287', '#FEE75C', '#EB459E', '#ED4245', 
              '#9B59B6', '#3498DB', '#2ECC71', '#F1C40F', '#E74C3C']
    
    if chart_type == 'pie':
        # Create pie chart
        total = sum(values)
        if total > 0:
            plt.pie(
                values,
                labels=[f"{label}" for label in labels],
                autopct=lambda p: f'{int(p * total / 100)}' if p > 5 else '',
                startangle=90,
                colors=colors[:len(labels)],
                wedgeprops={'linewidth': 1, 'edgecolor': '#2C2F33'}
            )
            
            # Add vote counts and percentages in legend
            plt.legend(
                title="Poll Results",
                labels=[f"{labels[i]}: {values[i]} votes ({values[i]/total*100:.1f}%)" 
                        for i in range(len(labels))],
                loc="center left",
                bbox_to_anchor=(1, 0.5)
            )
        else:
            plt.text(0.5, 0.5, 'No votes yet', horizontalalignment='center', 
                     verticalalignment='center', fontsize=18)
        
        plt.axis('equal')
    else:
        # Create bar chart with Discord style
        bars = plt.bar(
            range(len(labels)), 
            values, 
            color=colors[:len(labels)],
            edgecolor='#2C2F33',
            linewidth=1
        )
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width()/2., 
                height + 0.1,
                f'{int(height)}',
                ha='center', 
                va='bottom'
            )
        
        # Set x-axis labels with custom rotation
        plt.xticks(range(len(labels)), labels, rotation=30, ha='right')
        plt.ylabel('Votes')
        
        # Make sure labels are fully visible
        plt.tight_layout()
    
    # Set title and style
    plt.title(title, fontsize=16, pad=20)
    
    # Use Discord dark theme
    plt.gca().set_facecolor('#36393F')
    plt.gcf().set_facecolor('#36393F')
    plt.gca().tick_params(colors='white')
    plt.gca().xaxis.label.set_color('white')
    plt.gca().yaxis.label.set_color('white')
    plt.title(title, color='white')
    
    if chart_type == 'pie':
        plt.gca().legend().get_title().set_color('white')
        for text in plt.gca().legend().get_texts():
            text.set_color('white')
    
    # Save chart to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='#36393F', dpi=100)
    buf.seek(0)
    plt.close()
    
    return buf
