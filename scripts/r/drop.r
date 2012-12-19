library(ggplot2)
library(reshape)

df <- read.table("dropped_diff_reduced.txt", header = TRUE)
df <- melt(df, id="time")
df <- subset(df, df$value > 0)

p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
p <- p + geom_point(aes(size=value), alpha = 5/10) + scale_size(range = c(1, 3))
p <- p + opts(legend.position="none")
p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages dropped\n")
p

ggsave(file="dropped_diff.png")

df <- read.table("dropped_reduced.txt", header = TRUE)
df <- melt(df, id="time")

p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
p <- p + geom_line(alpha = 0.5)
p <- p + opts(legend.position="none")
p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages dropped\n")
p

ggsave(file="dropped.png")