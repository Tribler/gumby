library(ggplot2)
library(reshape)
library(RColorBrewer)

df <- read.table("send_diff_reduced.txt", header = TRUE)
df <- melt(df, id="time")
df <- subset(df, df$value > 0)
df$value = df$value/1024.0

p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
p <- p + geom_point(data = df, alpha=0.5)
p <- p + opts(legend.position="none")
p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage for peer (KB/s upload)\n")
p

dev.copy2pdf(file="send_diff.pdf", width=7, height=5)
embedFonts("send_diff.pdf",options="-dEmbedAllFonts=true -dPDFSETTINGS=/printer")

df <- read.table("received_diff_reduced.txt", header = TRUE, check.names = FALSE)
df <- melt(df, id="time")
df <- subset(df, df$value > 0)
df$value = df$value/1024.0

p <- ggplot(df, aes(time, value, group=variable, colour=type)) + theme_bw()
p <- p + geom_point(data = df, aes(size=value), alpha=0.5)
p <- p + opts(legend.position="none")
p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage for peer (KB/s download)\n")
p
dev.copy2pdf(file="received_diff.pdf", width=7, height=5)
embedFonts("received_diff.pdf",options="-dEmbedAllFonts=true -dPDFSETTINGS=/printer")

df <- read.table("send_reduced.txt", header = TRUE)
df <- melt(df, id="time")
df$value = df$value/1024.0

p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
p <- p + geom_line(alpha = 5/10)
p <- p + opts(legend.position="none")
p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage (KB/s upload)")
p

dev.copy2pdf(file="send.pdf")
dev.off()

df <- read.table("received_reduced.txt", header = TRUE)
df <- melt(df, id="time")
df$value = df$value/1024.0

p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
p <- p + geom_line(alpha = 5/10)
p <- p + opts(legend.position="none")
p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Bandwidth usage (KB/s download)")
p

dev.copy2pdf(file="received.pdf")