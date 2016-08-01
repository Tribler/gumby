create_comparison <- function(before, after, filename){
    # Calculate the maximum of both y scales to make sure they have matching scales
    y_max <- max(layer_scales(before)$y$range$range, layer_scales(before)$y$range$range)

    # Apply the new maximum y scale
    before <- before + ylim(0, y_max)
    after <- after + ylim(0, y_max)

    # Create the before-after-plot
    ggsave(file=filename, arrangeGrob(before, after, ncol=2), width=18, height=6, dpi=100)
}
